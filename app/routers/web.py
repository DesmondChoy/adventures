from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd
import logging
import uuid
import os
from typing import Dict, Any, Optional
from uuid import UUID as UUID_type  # To avoid conflict with uuid.uuid4()
from app.data.story_loader import StoryLoader
from app.services.state_storage_service import StateStorageService
from app.auth.dependencies import get_current_user_id_optional, get_current_user_id

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("story_app")


# Pydantic Models for API Response
class AdventureResumeDetails(BaseModel):
    adventure_id: UUID_type
    story_category: str
    lesson_topic: str
    current_chapter: int
    total_chapters: int = 10  # Assuming a fixed total for now
    last_updated: datetime


class CurrentAdventureAPIResponse(BaseModel):
    adventure: Optional[AdventureResumeDetails] = None


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


@router.get("/select")
async def select_adventure(request: Request):
    """Render the adventure selection page with story and lesson choices."""
    context = get_session_context(request)

    try:
        logger.info(
            "Loading adventure selection page",
            extra={**context, "path": "/select", "method": "GET"},
        )

        story_data = load_story_data()
        lesson_data = load_lesson_data()

        # Pass complete story data to template
        story_categories = story_data  # story_data already contains the categories

        logger.info(
            "Preparing adventure selection page data",
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
        logger.info(
            f"For /select route: SUPABASE_URL from env: '{supabase_url}', SUPABASE_ANON_KEY from env: '{supabase_anon_key}'"
        )  # DEBUG LOG

        return templates.TemplateResponse(
            "pages/index.html",  # Corrected path to use the index.html within 'pages'
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
            "Error rendering adventure selection page",
            extra={**context, "path": "/select", "method": "GET", "error": str(e)},
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
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        logger.info(
            f"For / route: SUPABASE_URL from env: '{supabase_url}', SUPABASE_ANON_KEY from env: '{supabase_anon_key}'"
        )  # DEBUG LOG
        return templates.TemplateResponse(
            "pages/login.html",  # Serve the new login page from templates
            {
                "request": request,
                "supabase_url": supabase_url,
                "supabase_anon_key": supabase_anon_key,
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


# --- New API Endpoints for Phase 4.1 ---


@router.get("/api/user/current-adventure", response_model=CurrentAdventureAPIResponse)
async def get_user_current_adventure_api(
    request: Request,
    user_id: Optional[UUID_type] = Depends(get_current_user_id_optional),
    state_storage_service: StateStorageService = Depends(
        StateStorageService
    ),  # Dependency inject service
):
    """
    API endpoint to get the current user's single incomplete adventure.
    Returns adventure details if found, otherwise null.
    """
    context = get_session_context(request)
    logger.info("[RESUME API DEBUG] /api/user/current-adventure called", extra=context)
    logger.info(f"[RESUME API DEBUG] Extracted user_id: {user_id}", extra=context)

    if not user_id:
        logger.info(
            "[RESUME API DEBUG] No user_id found - unauthenticated request",
            extra=context,
        )
        return CurrentAdventureAPIResponse(adventure=None)

    try:
        logger.info(
            f"[RESUME API DEBUG] Fetching current adventure for user {user_id}",
            extra=context,
        )
        # This method now needs to return a dict that matches AdventureResumeDetails structure
        # or we adapt it here.
        adventure_data = (
            await state_storage_service.get_user_current_adventure_for_resume(user_id)
        )
        logger.info(
            f"[RESUME API DEBUG] Adventure data from service: {adventure_data}",
            extra=context,
        )

        if adventure_data:
            # Adapt the dictionary from the service to the Pydantic model
            # The service method get_user_current_adventure_for_resume should ideally return
            # data in the shape expected by AdventureResumeDetails or be easily adaptable.
            # For now, assuming it returns a dict with the necessary keys.

            # Calculate current_chapter. If state_data is None or chapters is missing, default to 0 or 1.
            current_chapter_num = 0
            if adventure_data.get("state_data") and adventure_data["state_data"].get(
                "chapters"
            ):
                current_chapter_num = len(adventure_data["state_data"]["chapters"]) + 1
            elif (
                adventure_data.get("completed_chapter_count") is not None
            ):  # Fallback to completed_chapter_count
                current_chapter_num = (
                    adventure_data.get("completed_chapter_count", 0) + 1
                )

            adventure_details = AdventureResumeDetails(
                adventure_id=adventure_data[
                    "id"
                ],  # FIXED: Changed from "adventure_id" to "id"
                story_category=adventure_data["story_category"],
                lesson_topic=adventure_data["lesson_topic"],
                current_chapter=current_chapter_num,  # Needs to be calculated or retrieved
                total_chapters=adventure_data.get(
                    "total_chapters", 10
                ),  # Assuming 10 if not present
                last_updated=adventure_data["updated_at"],
            )
            logger.info(
                f"[RESUME API DEBUG] Returning adventure: {adventure_details.adventure_id}",
                extra=context,
            )
            return CurrentAdventureAPIResponse(adventure=adventure_details)

        logger.info(
            "[RESUME API DEBUG] No adventure found, returning null", extra=context
        )
        return CurrentAdventureAPIResponse(adventure=None)
    except Exception as e:
        logger.error(
            f"[RESUME API DEBUG] Error fetching current adventure for user {user_id}: {str(e)}",
            extra={**context, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Error fetching current adventure.")


@router.post("/api/adventure/{adventure_id}/abandon", status_code=200)
async def abandon_adventure_api(
    request: Request,
    adventure_id: str,
    user_id: UUID_type = Depends(get_current_user_id),  # Requires authentication
    state_storage_service: StateStorageService = Depends(StateStorageService),
):
    """
    API endpoint to mark an adventure as abandoned.
    Requires user to be authenticated.
    """
    context = get_session_context(request)  # For logging
    logger.info(
        f"User {user_id} attempting to abandon adventure {adventure_id}", extra=context
    )
    try:
        success = await state_storage_service.abandon_adventure(adventure_id, user_id)
        if success:
            logger.info(
                f"Adventure {adventure_id} successfully abandoned by user {user_id}",
                extra=context,
            )
            return {"message": "Adventure successfully abandoned."}
        else:
            logger.warning(
                f"Failed to abandon adventure {adventure_id} for user {user_id}. "
                f"It might not exist, not belong to the user, or already be complete.",
                extra=context,
            )
            raise HTTPException(
                status_code=404,
                detail="Adventure not found or cannot be abandoned by this user.",
            )
    except HTTPException:  # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.error(
            f"Error abandoning adventure {adventure_id} for user {user_id}: {str(e)}",
            extra={**context, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Error abandoning adventure.")
