# app/main.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import yaml
import pandas as pd
from typing import List, Dict, Any
import asyncio
from pydantic import BaseModel
from app.services.llm import LLMService
import uvicorn

# Initialize FastAPI app and services
app = FastAPI(title="Educational Story App")
llm_service = LLMService()  # Initialize LLM service

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# Load story and lesson data
def load_story_data() -> Dict[str, Any]:
    with open("app/data/stories.yaml", "r") as f:
        return yaml.safe_load(f)


def load_lesson_data() -> pd.DataFrame:
    return pd.read_csv("app/data/lessons.csv")


# Pydantic models for validation
class StoryChoice(BaseModel):
    text: str
    next_node: str


class StoryNode(BaseModel):
    content: str
    choices: List[StoryChoice]


class QuestionHistory(BaseModel):
    question: Dict[str, Any]
    chosen_answer: str
    was_correct: bool


class StoryState(BaseModel):
    current_node: str
    depth: int
    history: List[str]
    correct_answers: int
    total_questions: int
    previous_content: str | None = None
    question_history: List[QuestionHistory] = []  # Track all Q&A history


# Routes
@app.get("/")
async def root(request: Request):
    """Render the landing page with story and lesson choices."""
    story_data = load_story_data()
    lesson_data = load_lesson_data()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "story_categories": story_data["story_categories"].keys(),
            "lesson_topics": lesson_data["topic"].unique(),
        },
    )


@app.get("/story/{depth}")
async def story_page(request: Request, depth: int):
    """Render the story page for the given depth."""
    if depth < 1 or depth > 3:
        return {"error": "Invalid story depth"}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "story_categories": [],  # Empty as we'll use stored state
            "lesson_topics": [],  # Empty as we'll use stored state
        },
    )


@app.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()

    # Initialize with default state
    state = StoryState(
        current_node="start",
        depth=1,
        history=[],
        correct_answers=0,
        total_questions=0,
        previous_content=None,
        question_history=[],
    )

    try:
        while True:
            data = await websocket.receive_json()
            print(f"\nDEBUG: Received WebSocket data: {data}")

            choice = data.get("choice")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get(
                        "depth", 1
                    ),  # Default to 1 for first story page
                    history=data["state"].get("history", []),
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0),
                    previous_content=data["state"].get("previous_content", None),
                    question_history=data["state"].get("question_history", []),
                )
                print(f"\nDEBUG: Updated state from client: {state}")
                continue  # Skip to next iteration to wait for choice

            if choice is None:
                continue

            # Only append choice and increment depth for non-state messages
            if choice != "start":  # Don't append "start" to history
                state.history.append(choice)
                state.depth += 1

                # After answering a question at odd depths
                if state.depth % 2 == 0:
                    # Load the question that was just answered
                    lesson_data = load_lesson_data()
                    relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
                    if not relevant_lessons.empty:
                        answered_question = relevant_lessons.iloc[
                            state.total_questions % len(relevant_lessons)
                        ].to_dict()

                        # Record this Q&A in history
                        was_correct = choice == "correct"
                        state.question_history.append(
                            QuestionHistory(
                                question=answered_question,
                                chosen_answer=choice,
                                was_correct=was_correct,
                            )
                        )

                        if was_correct:
                            state.correct_answers += 1
                        state.total_questions += 1

                print(
                    f"\nDEBUG: Updated state after choice: depth={state.depth}, history={state.history}"
                )

            try:
                # Generate the complete story node
                story_node = await generate_story_node(
                    story_category, lesson_topic, state
                )

                # Split into paragraphs and stream each word while maintaining paragraph structure
                paragraphs = [
                    p.strip() for p in story_node.content.split("\n\n") if p.strip()
                ]

                # Process first paragraph
                if paragraphs:
                    words = paragraphs[0].split()
                    for word in words:
                        await websocket.send_text(word + " ")
                        await asyncio.sleep(0.05)  # Small delay between words

                # Process remaining paragraphs
                for paragraph in paragraphs[1:]:
                    # Send paragraph break
                    await websocket.send_text("\n\n")
                    await asyncio.sleep(0.2)  # Slightly longer pause between paragraphs

                    # Stream words in the paragraph
                    words = paragraph.split()
                    for word in words:
                        await websocket.send_text(word + " ")
                        await asyncio.sleep(0.05)  # Small delay between words

                # Send choices as a separate message
                await websocket.send_json(
                    {
                        "type": "choices",
                        "choices": [
                            {"text": choice.text, "id": choice.next_node}
                            for choice in story_node.choices
                        ],
                    }
                )
            except WebSocketDisconnect:
                print(f"Client disconnected during story generation")
                break
            except Exception as e:
                print(f"Error during story generation: {e}")
                await websocket.send_text(
                    "An error occurred while generating the story."
                )
                break

    except WebSocketDisconnect:
        print(f"Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure we handle any cleanup needed
        print(f"WebSocket connection closed")


async def generate_story_node(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Determine if we need an educational question (odd depths) or story choices (even depths)
    is_question_depth = state.depth % 2 == 1  # True for depths 1, 3, etc.

    # Load question for odd depths (including depth 1)
    question = None
    previous_questions = []

    # Get previous questions if we have history
    if state.question_history:
        previous_questions = [
            {
                "question": qh.question,
                "chosen_answer": qh.chosen_answer,
                "was_correct": qh.was_correct,
            }
            for qh in state.question_history
        ]
        print("\nDEBUG: Previous questions history:")
        for i, pq in enumerate(previous_questions, 1):
            print(f"Q{i}: {pq['question']['question']}")
            print(f"Chosen: {pq['chosen_answer']} (Correct: {pq['was_correct']})")

    # Load new question if at question depth
    if is_question_depth:
        lesson_data = load_lesson_data()
        print(f"\nDEBUG: Loading question at depth {state.depth}")
        print(
            f"DEBUG: Looking for topic '{lesson_topic}' in available topics: {lesson_data['topic'].unique()}"
        )

        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        print(f"DEBUG: Found {len(relevant_lessons)} lessons for topic {lesson_topic}")

        if not relevant_lessons.empty:
            question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            print(f"DEBUG: Selected question: {question['question']}")
            print(
                f"DEBUG: Choices: {question['correct_answer']}, {question['wrong_answer1']}, {question['wrong_answer2']}"
            )

    # Generate story content using LLM
    story_content = ""
    try:
        async for chunk in llm_service.generate_story_stream(
            story_config,
            state,
            question,  # Pass question for odd depths
            previous_questions,  # Pass all previous Q&A history
        ):
            story_content += chunk
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

    # Extract choices based on depth
    if is_question_depth and question:
        story_choices = [
            StoryChoice(text=question["correct_answer"], next_node="correct"),
            StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
            StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
        ]
    else:
        story_choices = [
            StoryChoice(text=f"Choice {i + 1}", next_node=f"node_{state.depth}_{i}")
            for i in range(2)
        ]

    # Debug output for choices
    print("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        print(f"Choice {i}: {choice.text} (next_node: {choice.next_node})")
    print("========================\n")

    # Store the current content for the next segment
    state.previous_content = story_content

    return StoryNode(content=story_content, choices=story_choices)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
