from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
import yaml
import pandas as pd
import logging
import uuid
from typing import Dict, Any

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("story_app")


def load_story_data() -> Dict[str, Any]:
    """Load story data with error handling."""
    try:
        with open("app/data/new_stories.yaml", "r") as f:
            data = yaml.safe_load(f)
            # Extract the story_categories from the loaded data
            story_categories = data.get("story_categories", {})
            logger.info(
                "Loaded story data",
                extra={
                    "categories": list(story_categories.keys()),
                    "elements_per_category": {
                        cat: list(details.keys())
                        for cat, details in story_categories.items()
                    },
                    "raw_data_keys": list(
                        data.keys()
                    ),  # Debug log to see top-level structure
                },
            )
            return story_categories
    except Exception as e:
        logger.error("Failed to load story data", extra={"error": str(e)})
        return {}  # Provide empty default value


def load_lesson_data() -> pd.DataFrame:
    """Load lesson data with error handling."""
    try:
        return pd.read_csv("app/data/lessons.csv")
    except Exception as e:
        logger.error("Failed to load lesson data", extra={"error": str(e)})
        return pd.DataFrame(columns=["topic"])  # Provide default value


def get_session_context(request: Request) -> dict:
    """Get session context for logging and tracking."""
    session = request.session
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    return {
        "session_id": session["session_id"],
        "request_id": session.get("request_id", "no_request_id"),
    }


@router.get("/")
async def root(request: Request):
    """Render the landing page with story and lesson choices."""
    context = get_session_context(request)

    try:
        logger.info(
            "Loading landing page", extra={**context, "path": "/", "method": "GET"}
        )

        story_data = load_story_data()
        lesson_data = load_lesson_data()

        # Pass complete story data to template
        story_categories = story_data  # story_data already contains the categories

        logger.info(
            "Preparing landing page data",
            extra={
                **context,
                "available_categories": list(story_categories.keys()),
                "available_topics": list(lesson_data["topic"].unique()),
            },
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "story_categories": story_categories,  # This now contains the complete category data
                "lesson_topics": lesson_data["topic"].unique(),
                **context,
            },
        )
    except Exception as e:
        logger.error(
            "Error rendering landing page",
            extra={**context, "path": "/", "method": "GET", "error": str(e)},
        )
        raise


@router.get("/story/{chapter}")
async def story_page(request: Request, chapter: int):
    """Render the story page for the given chapter."""
    try:
        # Validate chapter number
        if chapter < 1 or chapter > 7:  # Updated to match maximum story length
            logger.error(
                f"Invalid story chapter requested: {chapter}",
                extra={
                    "request_id": request.state.request_id,
                    "path": f"/story/{chapter}",
                    "status_code": 400,
                    "chapter": chapter,
                },
            )
            return {"error": "Invalid story chapter"}

        logger.info(
            f"Loading story page for chapter {chapter}",
            extra={
                "request_id": request.state.request_id,
                "path": f"/story/{chapter}",
                "status_code": 200,
                "chapter": chapter,
            },
        )
        return templates.TemplateResponse(
            "story.html",
            {"request": request},
        )
    except Exception as e:
        logger.error(
            f"Error rendering story page for chapter {chapter}",
            extra={
                "request_id": request.state.request_id,
                "path": f"/story/{chapter}",
                "status_code": 500,
                "chapter": chapter,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
