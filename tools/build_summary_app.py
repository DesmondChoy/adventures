"""
Build the React summary app and prepare it for use with the FastAPI application.

This script:
1. Installs the necessary dependencies for the React app
2. Builds the React app
3. Ensures the built files are accessible to the FastAPI application

Usage:
    python tools/build_summary_app.py

Requirements:
    - Node.js and npm must be installed
    - The React app must be in app/static/experimental/celebration-journey-moments-main
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("build_summary_app")

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REACT_APP_DIR = os.path.join(
    PROJECT_ROOT, "app", "static", "experimental", "celebration-journey-moments-main"
)
STATIC_DIR = os.path.join(PROJECT_ROOT, "app", "static")

# Node.js and npm paths
NODE_PATH = "C:\\Program Files\\nodejs\\node.exe"
NPM_PATH = "C:\\Program Files\\nodejs\\npm.cmd"


def check_node_npm():
    """Check if Node.js and npm are installed."""
    try:
        # Check Node.js using full path
        node_version = subprocess.run(
            [NODE_PATH, "--version"], capture_output=True, text=True, check=True
        )
        logger.info(f"Node.js version: {node_version.stdout.strip()}")

        # Check npm using full path
        npm_version = subprocess.run(
            [NPM_PATH, "--version"], capture_output=True, text=True, check=True
        )
        logger.info(f"npm version: {npm_version.stdout.strip()}")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking Node.js/npm: {e}")
        return False
    except FileNotFoundError:
        logger.error("Node.js or npm not found. Please install Node.js and npm.")
        return False


def install_dependencies():
    """Install the React app dependencies."""
    logger.info("Installing dependencies...")
    try:
        subprocess.run(
            [NPM_PATH, "install"],
            cwd=REACT_APP_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing dependencies: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def build_react_app():
    """Build the React app."""
    logger.info("Building React app...")
    try:
        subprocess.run(
            [NPM_PATH, "run", "build"],
            cwd=REACT_APP_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("React app built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error building React app: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return False


def ensure_static_files():
    """Ensure the built files are accessible to the FastAPI application."""
    dist_dir = os.path.join(REACT_APP_DIR, "dist")
    if not os.path.exists(dist_dir):
        logger.error(f"Build directory not found: {dist_dir}")
        return False

    # Check if index.html exists
    index_html = os.path.join(dist_dir, "index.html")
    if not os.path.exists(index_html):
        logger.error(f"index.html not found in build directory: {index_html}")
        return False

    logger.info("Static files are ready.")
    return True


def main():
    """Main function to build the React app."""
    logger.info("Starting build process for React summary app...")

    # Check if the React app directory exists
    if not os.path.exists(REACT_APP_DIR):
        logger.error(f"React app directory not found: {REACT_APP_DIR}")
        return 1

    # Check if Node.js and npm are installed
    if not check_node_npm():
        return 1

    # Install dependencies
    if not install_dependencies():
        return 1

    # Build the React app
    if not build_react_app():
        return 1

    # Ensure static files are accessible
    if not ensure_static_files():
        return 1

    logger.info("React summary app built successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
