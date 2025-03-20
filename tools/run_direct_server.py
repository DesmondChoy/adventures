"""
Run the FastAPI server directly using uvicorn.

This script:
1. Runs the FastAPI server directly using uvicorn
2. Sets the correct Python path

Usage:
    python tools/run_direct_server.py

Requirements:
    - Python dependencies must be installed
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("direct_server")

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def main():
    """Main function to run the FastAPI server directly."""
    logger.info("Starting FastAPI server directly using uvicorn...")

    # Set the Python path to include the project root
    env = {**os.environ, "PYTHONPATH": PROJECT_ROOT}

    # Run uvicorn directly
    try:
        # Use subprocess.run to run uvicorn directly
        result = subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--reload"],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
        )
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running uvicorn: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
