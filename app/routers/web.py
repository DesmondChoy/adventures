from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
import pandas as pd
import logging
import uuid
import os
from typing import Dict, Any
from app.data.story_loader import StoryLoader

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("story_app")


def load_story_data() -> Dict[str, Any]:
    """Load story data with error handling."""
    try:
        story_loader = StoryLoader()
        all_stories = story_loader.load_all_stories()
        story_categories = all_stories.get("story_categories", {})

        logger.info(
            "Loaded story data",
            extra={
                "categories_type": str(type(story_categories)),
                "categories_count": len(story_categories) if story_categories else 0,
                "categories": list(story_categories.keys()) if story_categories else [],
                "elements_per_category": {
                    cat: list(details.keys())
                    for cat, details in story_categories.items()
                }
                if story_categories
                else {},
            },
        )
        return story_categories
    except Exception as e:
        logger.error("Failed to load story data", extra={"error": str(e)})
        return {}  # Provide empty default value


def load_lesson_data() -> pd.DataFrame:
    """Load lesson data with error handling."""
    try:
        from app.data.lesson_loader import LessonLoader

        loader = LessonLoader()
        return loader.load_all_lessons()
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


@router.get("/adventure")
async def adventure(request: Request):
    """Render the adventure page with story and lesson choices."""
    context = get_session_context(request)

    try:
        logger.info(
            "Loading adventure page",
            extra={**context, "path": "/adventure", "method": "GET"},
        )

        story_data = load_story_data()
        lesson_data = load_lesson_data()

        # Pass complete story data to template
        story_categories = story_data  # story_data already contains the categories

        logger.info(
            "Preparing adventure page data",
            extra={
                **context,
                "available_categories": list(story_categories.keys()),
                "available_topics": list(lesson_data["topic"].unique()),
            },
        )

        # Create a dictionary mapping topics to their subtopics
        topic_subtopics = {}
        for topic in lesson_data["topic"].unique():
            # Get all subtopics for this topic
            topic_df = lesson_data[lesson_data["topic"] == topic]
            if "subtopic" in topic_df.columns:
                subtopics = topic_df["subtopic"].unique().tolist()
                topic_subtopics[topic] = subtopics
            else:
                topic_subtopics[topic] = []

        # Get Supabase environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "story_categories": story_categories,  # This now contains the complete category data
                "lesson_topics": lesson_data["topic"].unique(),
                "topic_subtopics": topic_subtopics,  # Add the topic to subtopics mapping
                "supabase_url": supabase_url,
                "supabase_anon_key": supabase_anon_key,
                **context,
            },
        )
    except Exception as e:
        logger.error(
            "Error rendering adventure page",
            extra={**context, "path": "/adventure", "method": "GET", "error": str(e)},
        )
        raise


@router.get("/")
async def root(request: Request):
    """Serve the landing page."""
    context = get_session_context(request)

    try:
        logger.info(
            "Loading landing page", extra={**context, "path": "/", "method": "GET"}
        )

        # Serve the landing page from static files
        return FileResponse("app/static/landing/index.html")
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
