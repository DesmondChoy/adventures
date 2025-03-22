from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import logging
import json
from app.models.story import ChapterType, AdventureState, ChapterContent, StoryChoice
from app.services.state_storage_service import StateStorageService
from app.services.adventure_state_manager import AdventureStateManager

router = APIRouter()
logger = logging.getLogger("summary_router")

# Initialize the state storage service
state_storage_service = StateStorageService()

# Directory for storing summary data
SUMMARY_DATA_DIR = "app/static"
SUMMARY_JSON_FILE = "adventure_summary_react.json"
SUMMARY_CHAPTER_DIR = "app/static/summary-chapter"


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
async def get_adventure_summary(state_id: Optional[str] = None):
    """API endpoint to get the adventure summary data.

    Args:
        state_id: Optional ID of the stored state to use for generating the summary.
                 If not provided, uses the current adventure state.
    """
    # Log the request parameters for debugging
    logger.info(f"get_adventure_summary called with state_id: {state_id}")

    # If state_id contains multiple values (e.g., from duplicate parameters), use the first one
    if state_id and "," in state_id:
        logger.warning(f"Multiple state_id values detected: {state_id}")
        state_id = state_id.split(",")[0]
        logger.info(f"Using first state_id value: {state_id}")
    try:
        # Create the adventure state manager
        state_manager = AdventureStateManager()

        # First try to get state from the state manager
        state = state_manager.get_current_state()

        # If no active state and state_id is provided, try to get from storage
        if not state and state_id:
            logger.info(f"No active state, trying to get stored state: {state_id}")

            # Log the memory cache contents for debugging
            logger.info(
                f"Memory cache keys before retrieval: {list(state_storage_service._memory_cache.keys())}"
            )

            # Get the stored state from the storage service
            stored_state = await state_storage_service.get_state(state_id)

            if stored_state:
                try:
                    logger.info(f"Retrieved state with ID: {state_id}")
                    logger.debug(f"State content keys: {list(stored_state.keys())}")

                    # Use the new method to reconstruct state from stored data
                    state = await state_manager.reconstruct_state_from_storage(
                        stored_state
                    )

                    if state:
                        logger.info(
                            f"Successfully reconstructed state with ID: {state_id}"
                        )
                    else:
                        logger.error("State reconstruction failed")
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to reconstruct adventure state",
                        )
                except Exception as e:
                    logger.error(f"Error reconstructing state: {str(e)}")
                    logger.error(f"State content that caused error: {stored_state}")
                    raise HTTPException(
                        status_code=500, detail=f"Error reconstructing state: {str(e)}"
                    )

        if not state:
            logger.warning("No active adventure state found")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No active adventure state found. Please complete an adventure to view the summary."
                },
            )

            # Check if the adventure is complete (has a CONCLUSION chapter)
            has_conclusion = False

            # Log all chapters for debugging
            logger.info(f"Total chapters: {len(state.chapters)}")

            # First check if chapter 10 exists (or the last chapter in a story of any length)
            last_chapter = None
            for ch in state.chapters:
                logger.info(
                    f"Chapter {ch.chapter_number}: type={ch.chapter_type}, raw_type={type(ch.chapter_type)}, value={str(ch.chapter_type)}"
                )

                # Keep track of the last chapter
                if (
                    last_chapter is None
                    or ch.chapter_number > last_chapter.chapter_number
                ):
                    last_chapter = ch

                # Check for CONCLUSION chapter with multiple conditions
                if (
                    # Check enum value
                    ch.chapter_type == ChapterType.CONCLUSION
                    # Check string value (case-insensitive)
                    or str(ch.chapter_type).lower() == "conclusion"
                    # Check chapter number (chapter 10 should be CONCLUSION)
                    or (ch.chapter_number == 10 and state.story_length == 10)
                    # Check if it's the last chapter in a story of any length
                    or (
                        ch.chapter_number == state.story_length
                        and state.story_length > 0
                    )
                ):
                    has_conclusion = True
                    logger.info(
                        f"Found CONCLUSION chapter: {ch.chapter_number} with type {ch.chapter_type}"
                    )
                    # Force set the chapter type to CONCLUSION if it's not already
                    if str(ch.chapter_type).lower() != "conclusion":
                        logger.warning(
                            f"Chapter {ch.chapter_number} has type {ch.chapter_type} but should be CONCLUSION. Treating as CONCLUSION."
                        )
                        # Actually update the chapter type to CONCLUSION
                        ch.chapter_type = ChapterType.CONCLUSION
                    break

            # If we didn't find a CONCLUSION chapter but we have a last chapter, check if it's chapter 10
            if not has_conclusion and last_chapter is not None:
                if (
                    last_chapter.chapter_number == 10
                    or last_chapter.chapter_number == state.story_length
                ):
                    logger.info(
                        f"Treating last chapter {last_chapter.chapter_number} as CONCLUSION chapter"
                    )
                    has_conclusion = True
                    # Update the chapter type to CONCLUSION
                    last_chapter.chapter_type = ChapterType.CONCLUSION

            if not has_conclusion:
                logger.warning("Adventure is not complete (no CONCLUSION chapter)")
                # Log more details about the state
                logger.warning(f"Story length: {state.story_length}")
                logger.warning(f"Planned chapter types: {state.planned_chapter_types}")
                logger.warning(f"Chapter count: {len(state.chapters)}")

                # Check if we have at least 9 chapters (all but the conclusion)
                if len(state.chapters) >= 9:
                    logger.info(
                        "We have at least 9 chapters, treating as complete adventure"
                    )
                    has_conclusion = True
                else:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Adventure is not complete. Complete the adventure to view the summary."
                        },
                    )

        # Format the adventure state data for the React summary component
        summary_data = state_manager.format_adventure_summary_data(state)

        return summary_data
    except Exception as e:
        logger.error(f"Error serving summary data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/store-adventure-state")
async def store_adventure_state(state_data: dict):
    """Store adventure state and return a unique ID."""
    try:
        state_id = await state_storage_service.store_state(state_data)
        return {"state_id": state_id}
    except Exception as e:
        logger.error(f"Error storing adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/get-adventure-state/{state_id}")
async def get_adventure_state(state_id: str):
    """Retrieve adventure state by ID."""
    try:
        state_data = await state_storage_service.get_state(state_id)
        if not state_data:
            raise HTTPException(status_code=404, detail="State not found or expired")
        return state_data
    except HTTPException:
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
