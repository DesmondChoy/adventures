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


@app.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()

    state = StoryState(
        current_node="start", depth=0, history=[], correct_answers=0, total_questions=0
    )

    try:
        while True:
            data = await websocket.receive_json()
            choice = data.get("choice")

            if choice is None:
                continue

            state.history.append(choice)
            state.depth += 1

            # Generate the complete story node
            story_node = await generate_story_segment(
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
        print(f"Client disconnected")


async def generate_story_segment(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate the next story segment based on the current state."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Load lesson data if we're at the question depth
    question = None
    if state.depth == 1:  # Next node will be depth 2
        lesson_data = load_lesson_data()
        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        question = relevant_lessons.iloc[state.total_questions].to_dict()

    # Generate story content using LLM
    story_stream = await llm_service.generate_story_segment(
        story_config, state, question
    )

    # Process the streaming response
    story_content = ""
    story_choices = []

    try:
        async for chunk in story_stream:
            if chunk.choices[0].delta.content:
                story_content += chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during story generation: {e}")
        story_content = "I apologize, but I encountered an error generating the story. Please try again."

    # Extract choices based on whether this is a question node or not
    if question:
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

    return StoryNode(content=story_content, choices=story_choices)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
