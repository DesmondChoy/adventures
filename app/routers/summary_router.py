from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import logging
import json

router = APIRouter()
logger = logging.getLogger("summary_router")

# Directory for storing summary data
SUMMARY_DATA_DIR = "app/static"
SUMMARY_JSON_FILE = "adventure_summary_react.json"
REACT_APP_DIR = "app/static/experimental/celebration-journey-moments-main"
REACT_APP_DIST_DIR = os.path.join(REACT_APP_DIR, "dist")


@router.get("/test-plain")
async def test_plain():
    """Test route that returns plain text."""
    logger.info("Serving test plain text")
    return "This is a test plain text response from the summary router"


@router.get("/summary")
async def summary_page(request: Request):
    """Serve the adventure summary page."""
    try:
        # Serve the React app index.html instead of the test HTML
        react_index_path = os.path.join(REACT_APP_DIST_DIR, "index.html")
        if not os.path.exists(react_index_path):
            logger.warning(f"React app index.html not found: {react_index_path}")
            # Fall back to test HTML if React app is not built
            test_html_path = os.path.join(SUMMARY_DATA_DIR, "test_summary.html")
            if os.path.exists(test_html_path):
                logger.info(f"Falling back to test HTML file: {test_html_path}")
                return FileResponse(test_html_path)
            return {"error": "Summary page not available. Please build the React app first."}

        # Serve the React app
        logger.info(f"Serving React app: {react_index_path}")
        return FileResponse(react_index_path)
    except Exception as e:
        logger.error(f"Error serving summary page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/adventure-summary")
async def get_adventure_summary():
    """API endpoint to get the adventure summary data."""
    try:
        # Check if the summary data file exists
        summary_file_path = os.path.join(SUMMARY_DATA_DIR, SUMMARY_JSON_FILE)
        if not os.path.exists(summary_file_path):
            logger.warning(f"Summary data file not found: {summary_file_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Summary data not found. Generate it first."},
            )

        # Read and return the summary data
        with open(summary_file_path, "r") as f:
            summary_data = json.load(f)

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
