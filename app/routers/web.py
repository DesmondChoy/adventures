from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
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
from app.models.story import AdventureState
from app.services.llm.prompt_templates import LOADING_PHRASES

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("story_app")


# Pydantic Models for API Response
class AdventureResumeDetails(BaseModel):
    adventure_id: UUID_type
    story_category: str
    lesson_topic: str
    current_chapter: int
    total_chapters: int = 10  # Will be set from AdventureState default in practice
    last_updated: datetime


class CurrentAdventureAPIResponse(BaseModel):
    adventure: Optional[AdventureResumeDetails] = None


def load_story_data() -> Dict[str, Any]:
    """Load story data with error handling."""
    try:
        story_loader = StoryLoader()
        all_stories = story_loader.load_all_stories()
        story_categories = all_stories.get("story_categories", {})

        logger.debug(
            f"Loaded {len(story_categories)} story categories",
            extra={"categories": list(story_categories.keys())} if story_categories else {},
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


def _adventure_data_to_resume(adventure_data: dict) -> Optional[AdventureResumeDetails]:
    """Convert adventure data dict to AdventureResumeDetails model.
    
    Args:
        adventure_data: Dictionary containing adventure data from storage
        
    Returns:
        AdventureResumeDetails model or None if data is invalid
    """
    if not adventure_data:
        return None
    
    # Validate required fields
    required_fields = ["id", "story_category", "lesson_topic", "updated_at"]
    if not all(adventure_data.get(field) for field in required_fields):
        return None
    
    # Calculate current chapter for display
    state_data = adventure_data.get("state_data")
    current_chapter_num = calculate_display_chapter_number(state_data)
    
    # Get display name from YAML
    story_loader = StoryLoader()
    story_display_name = story_loader.get_display_name(adventure_data["story_category"])
    
    return AdventureResumeDetails(
        adventure_id=adventure_data["id"],
        story_category=story_display_name,
        lesson_topic=adventure_data["lesson_topic"],
        current_chapter=current_chapter_num,
        total_chapters=adventure_data.get(
            "total_chapters", AdventureState.model_fields["story_length"].default
        ),
        last_updated=adventure_data["updated_at"],
    )


def calculate_display_chapter_number(state_data: dict | None) -> int:
    """
    Calculate the correct chapter number to display to the user.
    This matches the logic used in the WebSocket router and excludes SUMMARY chapters.
    """
    if not state_data or not isinstance(state_data, dict):
        return 1

    chapters = state_data.get("chapters", [])
    if not isinstance(chapters, list) or len(chapters) == 0:
        return 1

    # Filter out SUMMARY chapters from user display (same as summary processor)
    user_chapters = [
        chapter for chapter in chapters 
        if isinstance(chapter, dict) and chapter.get("chapter_type") != "summary"
    ]
    
    if not user_chapters:
        return 1

    # Default to next chapter number (internal tracking)
    display_chapter_number = len(user_chapters) + 1

    # Check if the last user-visible chapter has no response (will be re-sent)
    last_chapter = user_chapters[-1] if user_chapters else None
    if last_chapter and isinstance(last_chapter, dict):
        # If the last chapter has no response, user will see this chapter
        if last_chapter.get("response") is None:
            chapter_number = last_chapter.get("chapter_number")
            if chapter_number:
                display_chapter_number = chapter_number

    return display_chapter_number


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

    if not user_id:
        logger.info(
            "No user_id found for /api/user/current-adventure - unauthenticated request",
            extra=context,
        )
        return CurrentAdventureAPIResponse(adventure=None)

    try:
        logger.info(
            f"Fetching current adventure for user {user_id} via /api/user/current-adventure",
            extra=context,
        )

        # This method now needs to return a dict that matches AdventureResumeDetails structure
        # or we adapt it here.
        adventure_data = (
            await state_storage_service.get_user_current_adventure_for_resume(user_id)
        )

        if adventure_data:
            adventure_details = _adventure_data_to_resume(adventure_data)
            if not adventure_details:
                logger.error(
                    "Adventure data missing required fields in /api/user/current-adventure",
                    extra=context,
                )
                return CurrentAdventureAPIResponse(adventure=None)
            
            return CurrentAdventureAPIResponse(adventure=adventure_details)

        logger.info(
            f"No adventure found for user {user_id} in /api/user/current-adventure, returning null",
            extra=context,
        )
        return CurrentAdventureAPIResponse(adventure=None)

    except Exception as e:
        logger.error(
            f"Error fetching current adventure for user {user_id}: {str(e)}",
            extra={**context, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Error fetching current adventure.")


@router.get(
    "/api/adventure/active_by_client_uuid/{client_uuid}",
    response_model=CurrentAdventureAPIResponse,
)
async def get_active_adventure_by_client_uuid_api(
    request: Request,
    client_uuid: str,
    state_storage_service: StateStorageService = Depends(StateStorageService),
):
    """
    API endpoint to get the active adventure by client_uuid.
    This endpoint does not require JWT authentication.
    Returns adventure details if found, otherwise null.
    """
    context = get_session_context(request)
    logger.info(
        f"API call to /api/adventure/active_by_client_uuid/{client_uuid}",
        extra=context,
    )

    if not client_uuid:
        logger.warning(
            "client_uuid is missing in /api/adventure/active_by_client_uuid.",
            extra=context,
        )
        raise HTTPException(status_code=400, detail="Client UUID is required.")

    try:
        adventure_data = (
            await state_storage_service.get_active_adventure_by_client_uuid(client_uuid)
        )

        if adventure_data:
            adventure_details = _adventure_data_to_resume(adventure_data)
            if not adventure_details:
                logger.error(
                    f"Adventure for client_uuid {client_uuid} missing required fields in /api/adventure/active_by_client_uuid.",
                    extra=context,
                )
                return CurrentAdventureAPIResponse(adventure=None)
            
            return CurrentAdventureAPIResponse(adventure=adventure_details)

        logger.info(
            f"No adventure found for client_uuid {client_uuid} in /api/adventure/active_by_client_uuid, returning null",
            extra=context,
        )
        return CurrentAdventureAPIResponse(adventure=None)

    except Exception as e:
        logger.error(
            f"Error fetching active adventure for client_uuid {client_uuid}: {str(e)}",
            extra={**context, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Error fetching active adventure by client UUID."
        )


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


@router.get("/api/loading-phrases")
async def get_loading_phrases():
    """API endpoint to serve loading phrases for the loader component."""
    import random
    return {"phrases": LOADING_PHRASES}


@router.get("/debug/localStorage-inspector", response_class=HTMLResponse)
async def debug_localStorage_inspector(request: Request):
    """Debug dashboard for localStorage inspection and corruption tracking."""
    return templates.TemplateResponse(
        "debug/localStorage-inspector.html",
        {"request": request}
    )
