"""
Run the complete summary demo process.

This script:
1. Generates chapter summaries from a simulation state file
2. Builds the React app
3. Starts the FastAPI server

Usage:
    python tools/run_summary_demo.py [--state-file STATE_FILE] [--skip-build] [--skip-summaries]

Options:
    --state-file STATE_FILE  Path to the simulation state file to use
    --skip-build             Skip building the React app (use if already built)
    --skip-summaries         Skip generating summaries (use existing summary file)

Requirements:
    - Node.js and npm must be installed
    - Python dependencies must be installed
"""

import os
import sys
import subprocess
import argparse
import logging
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("summary_demo")

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REACT_APP_DIR = os.path.join(
    PROJECT_ROOT, "app", "static", "experimental", "celebration-journey-moments-main"
)
STATIC_DIR = os.path.join(PROJECT_ROOT, "app", "static")
OUTPUT_FILE = os.path.join(STATIC_DIR, "adventure_summary_react.json")


async def generate_summaries(state_file):
    """Generate chapter summaries from a simulation state file."""
    logger.info(f"Generating summaries from state file: {state_file}")

    # Import the generate_react_summary_data function
    sys.path.insert(0, PROJECT_ROOT)
    from tests.simulations.generate_chapter_summaries_react import (
        generate_react_summary_data,
    )

    # Generate the summaries
    try:
        await generate_react_summary_data(state_file, OUTPUT_FILE)
        logger.info(f"Summaries generated successfully: {OUTPUT_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error generating summaries: {e}")
        import traceback

        traceback.print_exc()
        return False


def build_react_app():
    """Build the React app."""
    logger.info("Building React app...")

    # Run the build script
    build_script = os.path.join(SCRIPT_DIR, "build_summary_app.py")
    try:
        result = subprocess.run(
            [sys.executable, build_script],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(result.stdout)
        logger.info("React app built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error building React app: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def start_server():
    """Start the FastAPI server."""
    logger.info("Starting FastAPI server...")

    try:
        # Use subprocess.Popen to start the server in the background
        # Use -m flag to run as a module, which ensures proper Python path
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=PROJECT_ROOT,  # Set working directory to project root
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **os.environ,
                "PYTHONPATH": PROJECT_ROOT,
            },  # Add project root to PYTHONPATH
        )

        # Wait a bit for the server to start
        import time

        time.sleep(2)

        # Check if the process is still running
        if process.poll() is None:
            logger.info("Server started successfully.")
            logger.info(
                "Visit http://localhost:8000/adventure/summary to view the summary page."
            )
            logger.info("Press Ctrl+C to stop the server.")

            # Keep the server running until the user presses Ctrl+C
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping server...")
                process.terminate()
                process.wait()
                logger.info("Server stopped.")
        else:
            # Process exited, get the output
            stdout, stderr = process.communicate()
            logger.error(f"Server exited unexpectedly with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return False


def find_latest_simulation_state():
    """Find the latest simulation state file."""
    logs_dir = os.path.join(PROJECT_ROOT, "logs", "simulations")

    # Check if the directory exists
    if not os.path.exists(logs_dir):
        logger.warning(f"Simulation logs directory not found: {logs_dir}")
        return None

    # Import the function from the original script
    sys.path.insert(0, PROJECT_ROOT)
    from tests.simulations.generate_chapter_summaries import (
        find_latest_simulation_state,
    )

    return find_latest_simulation_state()


def main():
    """Main function to run the summary demo."""
    parser = argparse.ArgumentParser(description="Run the summary demo process.")
    parser.add_argument(
        "--state-file",
        help="Path to the simulation state file to use",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building the React app (use if already built)",
    )
    parser.add_argument(
        "--skip-summaries",
        action="store_true",
        help="Skip generating summaries (use existing summary file)",
    )
    args = parser.parse_args()

    # Check if we should skip summary generation
    if args.skip_summaries:
        logger.info("Skipping summary generation.")
        # Check if the summary file exists
        if not os.path.exists(OUTPUT_FILE):
            logger.error(f"Summary file not found: {OUTPUT_FILE}")
            logger.error("Cannot skip summary generation if the file doesn't exist.")
            return 1
        logger.info(f"Using existing summary file: {OUTPUT_FILE}")
    else:
        # Get the state file
        state_file = args.state_file
        if not state_file:
            state_file = find_latest_simulation_state()
            if not state_file:
                logger.error(
                    "No simulation state file found. Please run a simulation first or specify a state file path."
                )
                return 1
            logger.info(
                f"Using latest simulation state file: {os.path.basename(state_file)}"
            )

        # Generate summaries
        if not asyncio.run(generate_summaries(state_file)):
            return 1

    # Build the React app (unless skipped)
    if not args.skip_build:
        if not build_react_app():
            return 1
    else:
        logger.info("Skipping React app build.")

    # Start the server
    if not start_server():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
