from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import logging
import json
from app.models.story import ChapterType

router = APIRouter()
logger = logging.getLogger("summary_router")

# Directory for storing summary data
SUMMARY_DATA_DIR = "app/static"
SUMMARY_JSON_FILE = "adventure_summary_react.json"
SUMMARY_CHAPTER_DIR = "app/static/summary-chapter"


@router.get("/test-plain")
async def test_plain():
    """Test route that returns plain text."""
    logger.info("Serving test plain text")
    return "This is a test plain text response from the summary router"


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
async def get_adventure_summary(adventure_id: Optional[str] = None):
    """API endpoint to get the adventure summary data.

    Args:
        adventure_id: Optional ID of the adventure to get summary for.
                     If not provided, returns the current adventure state.
    """
    try:
        # Get the adventure state manager
        from app.services.adventure_state_manager import AdventureStateManager

        state_manager = AdventureStateManager()

        # Get the current adventure state
        state = state_manager.get_current_state()

        if not state:
            logger.warning("No active adventure state found")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No active adventure state found. Please complete an adventure to view the summary."
                },
            )

        # Check if the adventure is complete (has a CONCLUSION chapter)
        if not any(ch.chapter_type == ChapterType.CONCLUSION for ch in state.chapters):
            logger.warning("Adventure is not complete (no CONCLUSION chapter)")
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
