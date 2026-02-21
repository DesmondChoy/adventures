from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
import os
import logging
from pathlib import Path
from uuid import UUID

from app.services.state_storage_service import StateStorageService
from app.services.summary import SummaryService, StateNotFoundError, SummaryError
from app.services.telemetry_service import TelemetryService
from app.utils.case_conversion import snake_to_camel_dict
from app.auth.dependencies import get_current_user_id_optional, get_current_user_id

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
    adventure_record = await summary_service.state_storage_service.get_adventure_record(
        state_id
    )
    if not adventure_record:
        raise HTTPException(status_code=404, detail="Adventure not found")

    state_data = adventure_record.get("state_data")
    if not isinstance(state_data, dict):
        logger.error(f"Adventure {state_id} has invalid state_data format")
        raise HTTPException(status_code=500, detail="Invalid adventure state data")

    adventure_user_id_str = adventure_record.get("user_id")

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
        raise HTTPException(
            status_code=400,
            detail="state_id query parameter is required",
        )

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
        raise HTTPException(status_code=500, detail="Error generating summary")
    except Exception as e:
        logger.error(f"Unexpected error serving summary data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/store-adventure-state")
async def store_adventure_state(
    state_data: dict,
    adventure_id: Optional[str] = None,
    user_id: UUID = Depends(get_current_user_id),
    summary_service: SummaryService = Depends(get_summary_service),
):
    """Store adventure state and return a unique ID."""
    try:
        if adventure_id:
            owns_adventure = (
                await summary_service.state_storage_service.is_adventure_owned_by_user(
                    adventure_id, user_id
                )
            )
            if not owns_adventure:
                logger.warning(
                    f"User {user_id} attempted to update non-owned adventure {adventure_id}"
                )
                raise HTTPException(status_code=403, detail="Access denied")

        # Store the state with the service
        state_id = await summary_service.store_adventure_state(
            state_data,
            adventure_id,
            user_id=user_id,
        )
        return {"state_id": state_id}
    except HTTPException:
        raise
    except SummaryError as e:
        logger.error(f"Error storing adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Error storing adventure state")
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


# Route to serve JavaScript files - this must be at the end to avoid catching other routes
@router.get("/{js_file:path}")
async def serve_js_file(js_file: str):
    """Serve JavaScript files from the summary chapter directory."""
    try:
        base_path = Path(SUMMARY_CHAPTER_DIR).resolve()
        resolved_path = (base_path / js_file).resolve()

        # Block traversal attempts by ensuring the final path remains inside base_path.
        if not resolved_path.is_relative_to(base_path):
            logger.warning(f"Blocked JS path traversal attempt: {js_file}")
            raise HTTPException(status_code=404, detail="Not found")

        if resolved_path.suffix != ".js":
            raise HTTPException(status_code=404, detail="Not found")

        if not resolved_path.is_file():
            logger.error(f"JavaScript file not found at: {resolved_path}")
            raise HTTPException(
                status_code=404, detail=f"JavaScript file {js_file} not found"
            )

        logger.info(f"Serving JavaScript file from: {resolved_path}")
        return FileResponse(str(resolved_path), media_type="application/javascript")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving JavaScript file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
