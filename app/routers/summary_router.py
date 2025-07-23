from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import os
import logging
import json
from uuid import UUID

from app.models.story import AdventureState
from app.services.state_storage_service import StateStorageService
from app.services.summary import SummaryService, StateNotFoundError, SummaryError
from app.services.telemetry_service import TelemetryService
from app.utils.case_conversion import snake_to_camel_dict
from app.auth.dependencies import get_current_user_id_optional

# Configure logger
logger = logging.getLogger("summary_router")

# Lazy instantiation to avoid environment variable loading issues during import
_telemetry_service = None


def get_telemetry_service():
    """Get or create the telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service


# Directory paths
SUMMARY_DATA_DIR = "app/static"
SUMMARY_JSON_FILE = "adventure_summary_react.json"
SUMMARY_CHAPTER_DIR = "app/static/summary-chapter"


def get_summary_service():
    """Dependency injection for SummaryService."""
    state_storage_service = StateStorageService()
    return SummaryService(state_storage_service)


async def validate_user_adventure_access(
    state_id: str, user_id: Optional[UUID], summary_service: SummaryService
) -> dict:
    """
    Validate that the user has access to the adventure.
    Returns the state_data if access is allowed, raises HTTPException otherwise.
    """
    # Get the raw state data to check ownership
    state_data = await summary_service.state_storage_service.get_state(state_id)
    if not state_data:
        raise HTTPException(status_code=404, detail="Adventure not found")

    # Check ownership
    adventure_user_id_str = None

    # Check for user_id in metadata first
    if "metadata" in state_data and "user_id" in state_data["metadata"]:
        adventure_user_id_str = state_data["metadata"]["user_id"]
    # Fallback to top-level user_id
    elif "user_id" in state_data:
        adventure_user_id_str = state_data["user_id"]

    # If adventure has no user_id (guest adventure), allow access
    if adventure_user_id_str is None:
        logger.info(f"Allowing access to guest adventure {state_id}")
        return state_data

    # If user is not authenticated, deny access to user adventures
    if not user_id:
        logger.warning(
            f"Unauthenticated user attempted access to user adventure {state_id}"
        )
        raise HTTPException(status_code=403, detail="Authentication required")

    # Check if the authenticated user owns this adventure
    if adventure_user_id_str != str(user_id):
        logger.warning(
            f"User {user_id} attempted access to adventure {state_id} owned by {adventure_user_id_str}"
        )
        raise HTTPException(status_code=403, detail="Access denied: not your adventure")

    logger.info(f"User {user_id} granted access to their adventure {state_id}")
    return state_data


# Create router
router = APIRouter()


@router.get("/summary")
async def summary_page(request: Request):
    """Serve the adventure summary page."""
    try:
        # Check if the app is available in the new location
        new_index_path = os.path.join(SUMMARY_CHAPTER_DIR, "index.html")
        if os.path.exists(new_index_path):
            logger.info(f"Serving React app from: {new_index_path}")
            return FileResponse(new_index_path)

        # Fall back to test HTML if React app is not built
        test_html_path = os.path.join(SUMMARY_DATA_DIR, "test_summary.html")
        if os.path.exists(test_html_path):
            logger.info(f"Falling back to test HTML file: {test_html_path}")
            return FileResponse(test_html_path)

        # If no options are available, return an error
        logger.warning("Summary page not found")
        return {
            "error": "Summary page not available. Please build the React app first."
        }
    except Exception as e:
        logger.error(f"Error serving summary page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-plain")
async def test_plain():
    """Test route that returns plain text."""
    logger.info("Serving test plain text")
    return "This is a test plain text response from the summary router"


@router.get("/api/adventure-summary")
async def get_adventure_summary(
    state_id: Optional[str] = None,
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
    summary_service: SummaryService = Depends(get_summary_service),
):
    """API endpoint to get the adventure summary data.

    Args:
        state_id: Optional ID of the stored state to use for generating the summary.
               If not provided, uses the current adventure state.
        user_id: Optional authenticated user ID for security validation.
        summary_service: Injected SummaryService
    """
    # Log the request parameters for debugging
    logger.info(
        f"get_adventure_summary called with state_id: {state_id}, user_id: {user_id}"
    )

    # Check if state_id is provided
    if not state_id:
        logger.warning("No state_id provided to get_adventure_summary")
        # Create minimal mock data for testing if needed
        mock_data = {
            "chapterSummaries": [
                {
                    "number": 1,
                    "title": "Chapter 1: The Beginning",
                    "summary": "This is a sample summary for testing. You can start a real adventure to see actual chapter summaries.",
                    "chapterType": "story",
                },
                {
                    "number": 2,
                    "title": "Chapter 2: The Journey",
                    "summary": "This is another sample summary. Real adventures will have actual content here based on your choices.",
                    "chapterType": "story",
                },
            ],
            "educationalQuestions": [
                {
                    "question": "Would you like to go on an educational adventure?",
                    "userAnswer": "Yes",
                    "isCorrect": True,
                    "explanation": "Great! Click the Start button to begin a new adventure.",
                }
            ],
            "statistics": {
                "chaptersCompleted": 2,
                "questionsAnswered": 1,
                "timeSpent": "5 mins",
                "correctAnswers": 1,
            },
        }
        logger.info("Returning mock data for testing")
        return mock_data

    # If state_id contains multiple values (e.g., from duplicate parameters), use the first one
    if "," in state_id:
        logger.warning(f"Multiple state_id values detected: {state_id}")
        state_id = state_id.split(",")[0].strip()
        logger.info(f"Using first state_id value: {state_id}")

    try:
        # SECURITY: Validate user access to this adventure before proceeding
        state_data = await validate_user_adventure_access(
            state_id, user_id, summary_service
        )

        # Get adventure state from storage or active state
        logger.info(f"Getting adventure state from ID: {state_id}")
        adventure_state = await summary_service.get_adventure_state_from_id(state_id)

        # Ensure the last chapter is properly identified as a CONCLUSION chapter
        logger.info("Ensuring CONCLUSION chapter is properly identified")
        adventure_state = summary_service.ensure_conclusion_chapter(adventure_state)

        # Log summary_viewed event with deduplication
        if adventure_state:
            try:
                # Check if we've already logged a summary_viewed event for this adventure recently (within 5 minutes)
                from datetime import datetime, timedelta
                
                recent_cutoff = datetime.now() - timedelta(minutes=5)
                
                # Query for recent summary_viewed events for this adventure
                telemetry_service = get_telemetry_service()
                recent_events = telemetry_service.supabase.table("telemetry_events").select("id").eq(
                    "event_name", "summary_viewed"
                ).eq(
                    "adventure_id", state_id
                ).gte(
                    "timestamp", recent_cutoff.isoformat()
                ).execute()
                
                if recent_events.data and len(recent_events.data) > 0:
                    logger.info(
                        f"Skipping 'summary_viewed' event for adventure ID: {state_id} - already logged recently ({len(recent_events.data)} events in last 5 mins)"
                    )
                else:
                    event_metadata = {
                        "story_category": adventure_state.metadata.get("story_category"),
                        "lesson_topic": adventure_state.metadata.get("lesson_topic"),
                        "client_uuid": adventure_state.metadata.get("client_uuid"),
                        "chapters_in_summary": len(adventure_state.chapters)
                        if adventure_state.chapters
                        else 0,
                    }
                    event_metadata = {
                        k: v for k, v in event_metadata.items() if v is not None
                    }

                    await telemetry_service.log_event(
                        event_name="summary_viewed",
                        adventure_id=UUID(state_id) if state_id else None,
                        user_id=user_id,  # Use the authenticated user_id
                        metadata=event_metadata,
                        chapter_type="summary",  # Added
                        chapter_number=None,  # Added
                    )
                    logger.info(
                        f"Logged 'summary_viewed' event for adventure ID: {state_id}"
                    )
            except Exception as tel_e:
                logger.error(f"Error logging 'summary_viewed' event: {tel_e}")

        # Format the adventure state data for the React summary component
        logger.info("Formatting adventure summary data")
        summary_data = await summary_service.format_adventure_summary_data(adventure_state, state_id)

        # Convert all keys from snake_case to camelCase at the API boundary
        camel_case_data = snake_to_camel_dict(summary_data)

        logger.info("Returning formatted summary data to React app")
        return camel_case_data
    except HTTPException:
        # Re-raise HTTP exceptions (from validation)
        raise
    except StateNotFoundError as e:
        logger.warning(f"State not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except SummaryError as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error serving summary data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error serving summary data: {str(e)}"
        )


@router.post("/api/store-adventure-state")
async def store_adventure_state(
    state_data: dict,
    adventure_id: Optional[str] = None,
    summary_service: SummaryService = Depends(get_summary_service),
):
    """Store adventure state and return a unique ID."""
    try:
        # Store the state with the service
        state_id = await summary_service.store_adventure_state(state_data, adventure_id)
        return {"state_id": state_id}
    except SummaryError as e:
        logger.error(f"Error storing adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error storing adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/get-adventure-state/{state_id}")
async def get_adventure_state(
    state_id: str,
    user_id: Optional[UUID] = Depends(get_current_user_id_optional),
    summary_service: SummaryService = Depends(get_summary_service),
):
    """Retrieve adventure state by ID with user ownership validation."""
    try:
        # SECURITY: Validate user access to this adventure before proceeding
        state_data = await validate_user_adventure_access(
            state_id, user_id, summary_service
        )

        logger.info(f"User {user_id} successfully retrieved adventure state {state_id}")
        return state_data
    except HTTPException:
        # Re-raise HTTP exceptions (from validation)
        raise
    except Exception as e:
        logger.error(f"Error retrieving adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/generate-summary/{state_file_id}")
async def generate_summary(state_file_id: str):
    """Generate a summary from a simulation state file."""
    try:
        # This would normally call the generate_chapter_summaries_react.py script
        # For now, we'll just return a message
        return {
            "message": f"Summary generation from state file {state_file_id} would be triggered here.",
            "note": "This endpoint is a placeholder. Implement the actual generation logic in production.",
        }
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Route to serve JavaScript files - this must be at the end to avoid catching other routes
@router.get("/{js_file:path}")
async def serve_js_file(js_file: str):
    """Serve JavaScript files from the summary chapter directory."""
    if not js_file.endswith(".js"):
        raise HTTPException(status_code=404, detail="Not found")

    try:
        js_path = os.path.join(SUMMARY_CHAPTER_DIR, js_file)
        if os.path.exists(js_path):
            logger.info(f"Serving JavaScript file from: {js_path}")
            return FileResponse(js_path, media_type="application/javascript")
        else:
            logger.error(f"JavaScript file not found at: {js_path}")
            raise HTTPException(
                status_code=404, detail=f"JavaScript file {js_file} not found"
            )
    except Exception as e:
        logger.error(f"Error serving JavaScript file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
