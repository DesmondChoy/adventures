from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import yaml
import pandas as pd

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Load story and lesson data
def load_story_data():
    with open("app/data/stories.yaml", "r") as f:
        return yaml.safe_load(f)


def load_lesson_data():
    return pd.read_csv("app/data/lessons.csv")


@router.get("/")
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


@router.get("/story/{depth}")
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
