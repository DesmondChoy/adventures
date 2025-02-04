from fastapi import APIRouter, Request
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
        with open("app/data/stories.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load story data", extra={"error": str(e)})
        return {"story_categories": {}}  # Provide default value


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

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "story_categories": story_data["story_categories"].keys(),
                "lesson_topics": lesson_data["topic"].unique(),
                **context,  # Pass session context to template
            },
        )
    except Exception as e:
        logger.error(
            "Error rendering landing page",
            extra={**context, "path": "/", "method": "GET", "error": str(e)},
        )
        raise


@router.get("/story/{depth}")
async def story_page(request: Request, depth: int):
    """Render the story page for the given depth."""
    context = get_session_context(request)

    if depth < 1 or depth > 3:
        logger.warning(
            f"Invalid story depth requested: {depth}",
            extra={
                **context,
                "path": f"/story/{depth}",
                "method": "GET",
                "depth": depth,
            },
        )
        return {"error": "Invalid story depth"}

    try:
        logger.info(
            f"Loading story page for depth {depth}",
            extra={
                **context,
                "path": f"/story/{depth}",
                "method": "GET",
                "depth": depth,
            },
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "story_categories": [],  # Empty as we'll use stored state
                "lesson_topics": [],  # Empty as we'll use stored state
                **context,  # Pass session context to template
            },
        )
    except Exception as e:
        logger.error(
            f"Error rendering story page for depth {depth}",
            extra={
                **context,
                "path": f"/story/{depth}",
                "method": "GET",
                "depth": depth,
                "error": str(e),
            },
        )
        raise
