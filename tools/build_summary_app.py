#!/usr/bin/env python3
"""
Build script for the Summary Chapter React application.

This script handles both development and production builds of the React app,
ensuring the output is correctly placed in the expected location for serving.

Usage:
    python tools/build_summary_app.py --mode [development|production]
    python tools/build_summary_app.py --mode production --output-dir app/static/custom-location
    python tools/build_summary_app.py --mode production --skip-install

Options:
    --mode              Build mode: 'development' or 'production' (default: production)
    --output-dir        Directory where the built app should be placed (default: app/static/summary-chapter)
    --skip-install      Skip npm dependency installation
    --verbose           Enable verbose output
"""

import argparse
import os
import subprocess
import sys
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("build_summary_app")

# Constants
REACT_APP_DIR = "app/static/experimental/celebration-journey-moments-main"
DEFAULT_OUTPUT_DIR = "app/static/summary-chapter"


def check_node_npm():
    """Check if Node.js and npm are installed."""
    try:
        node_version = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, check=True
        )
        npm_version = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, check=True
        )
        logger.info(f"Node.js version: {node_version.stdout.strip()}")
        logger.info(f"npm version: {npm_version.stdout.strip()}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Node.js or npm not found. Please install them and try again.")
        return False


def install_dependencies(app_dir, verbose=False):
    """Install npm dependencies."""
    logger.info("Installing npm dependencies...")

    npm_cmd = ["npm", "install"]
    if not verbose:
        npm_cmd.append("--quiet")

    try:
        subprocess.run(npm_cmd, cwd=app_dir, check=True)
        logger.info("Dependencies installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def build_app(app_dir, mode="production", verbose=False):
    """Build the React app."""
    logger.info(f"Building React app in {mode} mode...")

    # Determine the build command based on mode
    if mode == "production":
        build_cmd = ["npm", "run", "build"]
    else:  # development
        build_cmd = ["npm", "run", "build:dev"]

    if not verbose:
        build_cmd.append("--quiet")

    try:
        subprocess.run(build_cmd, cwd=app_dir, check=True)
        logger.info(f"React app built successfully in {mode} mode.")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to build React app: {e}")
        return False


def copy_build_output(app_dir, output_dir):
    """Copy the build output to the specified directory."""
    build_dir = os.path.join(app_dir, "dist")

    if not os.path.exists(build_dir):
        logger.error(f"Build directory not found: {build_dir}")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Remove existing files in output directory
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

        # Copy all files from build directory to output directory
        for item in os.listdir(build_dir):
            src = os.path.join(build_dir, item)
            dst = os.path.join(output_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        logger.info(f"Build output copied to {output_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy build output: {e}")
        return False


def start_dev_server(app_dir, verbose=False):
    """Start the development server."""
    logger.info("Starting development server...")

    dev_cmd = ["npm", "run", "dev"]
    if not verbose:
        dev_cmd.append("--quiet")

    try:
        # Run the development server (this will block until terminated)
        subprocess.run(dev_cmd, cwd=app_dir, check=True)
    except KeyboardInterrupt:
        logger.info("Development server stopped.")
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to start development server: {e}")
        return False

    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build the Summary Chapter React app.")
    parser.add_argument(
        "--mode",
        choices=["development", "production"],
        default="production",
        help="Build mode: 'development' or 'production' (default: production)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory where the built app should be placed (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip npm dependency installation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Get absolute paths
    app_dir = os.path.abspath(REACT_APP_DIR)
    output_dir = os.path.abspath(args.output_dir)

    logger.info(f"React app directory: {app_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Build mode: {args.mode}")

    # Check if Node.js and npm are installed
    if not check_node_npm():
        return 1

    # Check if the React app directory exists
    if not os.path.exists(app_dir):
        logger.error(f"React app directory not found: {app_dir}")
        return 1

    # Install dependencies if not skipped
    if not args.skip_install:
        if not install_dependencies(app_dir, args.verbose):
            return 1
    else:
        logger.info("Skipping dependency installation.")

    # Handle development mode
    if args.mode == "development":
        logger.info("Starting development server...")
        return 0 if start_dev_server(app_dir, args.verbose) else 1

    # Handle production mode
    if not build_app(app_dir, args.mode, args.verbose):
        return 1

    if not copy_build_output(app_dir, output_dir):
        return 1

    logger.info(f"Summary Chapter React app built successfully in {args.mode} mode.")
    logger.info(f"The app is available at: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
