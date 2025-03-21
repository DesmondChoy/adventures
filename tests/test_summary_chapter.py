"""
Test script for debugging the summary chapter without generating all 10 chapters.

This script:
1. Finds a simulation state file (or uses one you specify)
2. Generates formatted summary data from that file
3. Starts a temporary FastAPI server with a test endpoint
4. Opens a browser to view the summary page with the generated data

This allows you to test and debug the summary chapter without having to generate
all 10 chapters of an adventure first. It uses existing simulation state files
from previous runs.

Requirements:
- uvicorn (pip install uvicorn)
- fastapi (pip install fastapi)
- The React summary app must be built (run tools/build_summary_app.py first)
- At least one simulation state file in logs/simulations/ directory

Usage:
    # Use the latest simulation state file:
    python tests/test_summary_chapter.py

    # Use a specific simulation state file:
    python tests/test_summary_chapter.py --state-file logs/simulations/your_file.json

    # Use a different port (default is 8001):
    python tests/test_summary_chapter.py --port 8080
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import webbrowser
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, project_root)

# Import the generate_react_summary_data function
from tests.simulations.generate_chapter_summaries import (
    generate_react_summary_data,
    find_latest_simulation_state,
)

# Create a temporary FastAPI app for testing
app = FastAPI(title="Summary Chapter Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the summary data
summary_data: Dict[str, Any] = {}


@app.get("/api/adventure-summary")
async def get_test_summary():
    """Test endpoint that serves the generated summary data."""
    if not summary_data:
        raise HTTPException(status_code=404, detail={"error": "Summary data not found"})
    return summary_data


@app.get("/adventure/api/adventure-summary")
async def get_adventure_summary():
    """Alias for the test endpoint to match the production URL structure."""
    return await get_test_summary()


@app.get("/summary")
@app.get("/adventure/summary")
async def summary_page():
    """Serve the summary page."""
    summary_page_path = os.path.join(
        project_root, "app/static/summary-chapter/index.html"
    )
    if os.path.exists(summary_page_path):
        return FileResponse(summary_page_path)
    else:
        raise HTTPException(
            status_code=404,
            detail="Summary page not found. Make sure the React app is built.",
        )


# Mount static files
app.mount(
    "/assets",
    StaticFiles(
        directory=os.path.join(project_root, "app/static/summary-chapter/assets")
    ),
    name="assets",
)

# Mount the same assets at the /adventure/assets path to match production
app.mount(
    "/adventure/assets",
    StaticFiles(
        directory=os.path.join(project_root, "app/static/summary-chapter/assets")
    ),
    name="adventure_assets",
)


async def generate_summary_data(state_file: str) -> Dict[str, Any]:
    """Generate summary data from a simulation state file."""
    # Create a temporary file to store the data
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Generate the summary data
        data = await generate_react_summary_data(state_file, temp_path)
        return data
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


async def main(state_file: Optional[str] = None, port: int = 8001):
    """Main function to run the test server."""
    global summary_data

    # Check if the React app is built
    summary_page_path = os.path.join(
        project_root, "app/static/summary-chapter/index.html"
    )
    assets_path = os.path.join(project_root, "app/static/summary-chapter/assets")

    if not os.path.exists(summary_page_path) or not os.path.exists(assets_path):
        print(
            "ERROR: Summary page or assets not found. Please build the React app first by running:"
        )
        print("    python tools/build_summary_app.py")
        sys.exit(1)

    # Find a simulation state file if not provided
    if not state_file:
        state_file = find_latest_simulation_state()
        if not state_file:
            print(
                "ERROR: No simulation state files found. Please run a simulation first or specify a state file path."
            )
            sys.exit(1)

    print(f"Using simulation state file: {os.path.basename(state_file)}")

    # Generate summary data
    print("Generating summary data...")
    summary_data = await generate_summary_data(state_file)
    print(
        f"Generated summary data with {len(summary_data['chapterSummaries'])} chapters"
    )

    # Start the server
    print(f"Starting test server on http://localhost:{port}")
    config = uvicorn.Config(app=app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)

    # Open the browser
    webbrowser.open(f"http://localhost:{port}/adventure/summary")

    # Run the server
    await server.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the summary chapter with simulation data"
    )
    parser.add_argument("--state-file", help="Path to a simulation state file")
    parser.add_argument(
        "--port", type=int, default=8001, help="Port to run the test server on"
    )
    args = parser.parse_args()

    asyncio.run(main(args.state_file, args.port))
