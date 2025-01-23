# app/main.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import yaml
import pandas as pd
from typing import List, Dict, Any
import asyncio
from pydantic import BaseModel
from app.services.llm import LLMService
from fastapi.responses import StreamingResponse
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


class StoryState(BaseModel):
    current_node: str
    depth: int
    history: List[str]
    correct_answers: int
    total_questions: int


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
        current_node="start", depth=1, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get("depth", 1),  # Default to 1 instead of 0
                    history=data["state"].get("history", []),
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0),
                )
                continue  # Skip to next iteration to wait for choice

            if choice is None:
                continue

            # Only append choice and increment depth for non-state messages
            if choice != "start":  # Don't append "start" to history
                state.history.append(choice)
                state.depth += 1

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
    if is_question_depth:
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        if not relevant_lessons.empty:
            question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config,
        state,
        question,  # Always pass question for odd depths
    )

    # Process the streaming response
    story_content = ""
    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

    # Remove any story choices if this is a question depth
    if is_question_depth:
        # Remove any lines containing "What should" or similar choice prompts
        lines = story_content.split("\n")
        story_content = "\n".join(
            line
            for line in lines
            if not any(
                prompt in line.lower()
                for prompt in [
                    "what should",
                    "should he",
                    "would you",
                    "- ",
                    "1.",
                    "2.",
                    "3.",
                ]
            )
        )

    # Set up choices based on depth
    if is_question_depth and question:
        # Educational question choices at odd depths
        story_choices = [
            StoryChoice(text=question["correct_answer"], next_node="correct"),
            StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
            StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
        ]

        # Only append the question if it's not already in the story
        if question["question"] not in story_content:
            story_content += f"\n\n{question['question']}"
    else:
        # Story-driven choices at even depths
        story_choices = [
            StoryChoice(text=choice["text"], next_node=f"node_{state.depth}_{i}")
            for i, choice in enumerate(
                [
                    {
                        "text": "Trust his instincts and search for the Silverleaf Fern on his own"
                    },
                    {
                        "text": "Ask the wise old owl for guidance and learn more about the garden"
                    },
                ]
            )
        ]

    return StoryNode(content=story_content, choices=story_choices)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
