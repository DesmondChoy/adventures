#!/usr/bin/env python3
"""
Build script for the Summary Chapter React application.

This script handles both development and production builds of the React app,
ensuring the output is correctly placed in the expected location for serving.

Usage:
    python tools/build_summary_app.py --mode [development|production]
    python tools/build_summary_app.py --mode production --output-dir app/static/custom-location
    python tools/build_summary_app.py --mode production --skip-install
    python tools/build_summary_app.py --mode production --node-path /path/to/node --npm-path /path/to/npm

Options:
    --mode              Build mode: 'development' or 'production' (default: production)
    --output-dir        Directory where the built app should be placed (default: app/static/summary-chapter)
    --skip-install      Skip npm dependency installation
    --verbose           Enable verbose output
    --node-path         Specify the path to the Node.js executable (useful if auto-detection fails)
    --npm-path          Specify the path to the npm executable (useful if auto-detection fails)
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
    # Try multiple possible locations for Node.js and npm
    possible_node_paths = [
        "node",  # Standard PATH resolution
        "C:\\Program Files\\nodejs\\node.exe",  # Common Windows location
        os.path.expandvars("%APPDATA%\\npm\\node.exe"),  # npm global install location
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\current\\node.exe"
        ),  # NVM location
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\v22.13.1\\node.exe"
        ),  # Specific NVM version
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\latest\\node.exe"
        ),  # Latest NVM version
        "C:\\Program Files\\nodejs\\node.exe",  # Standard install location
        "C:\\nodejs\\node.exe",  # Alternative install location
    ]

    possible_npm_paths = [
        "npm",  # Standard PATH resolution
        "C:\\Program Files\\nodejs\\npm.cmd",  # Common Windows location
        os.path.expandvars("%APPDATA%\\npm\\npm.cmd"),  # npm global install location
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\current\\npm.cmd"
        ),  # NVM location
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\v22.13.1\\npm.cmd"
        ),  # Specific NVM version
        os.path.expanduser(
            "~\\AppData\\Roaming\\nvm\\latest\\npm.cmd"
        ),  # Latest NVM version
        "C:\\Program Files\\nodejs\\npm.cmd",  # Standard install location
        "C:\\nodejs\\npm.cmd",  # Alternative install location
    ]

    # Try to find node executable
    node_path = None
    for path in possible_node_paths:
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, check=True
            )
            node_path = path
            logger.info(f"Found Node.js at {path}: {result.stdout.strip()}")
            break
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Node.js not found at {path}: {str(e)}")

    # Try to find npm executable
    npm_path = None
    for path in possible_npm_paths:
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, check=True
            )
            npm_path = path
            logger.info(f"Found npm at {path}: {result.stdout.strip()}")
            break
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"npm not found at {path}: {str(e)}")

    if node_path and npm_path:
        return True, node_path, npm_path

    # Print diagnostic information
    logger.error("Node.js or npm not found. Please install them and try again.")
    logger.error("PATH environment variable: " + os.environ.get("PATH", "Not found"))
    logger.error("Current working directory: " + os.getcwd())

    # Additional diagnostics
    logger.error("\nDiagnostic information:")
    logger.error("Checked the following Node.js paths:")
    for path in possible_node_paths:
        logger.error(f"  - {path}")
    logger.error("Checked the following npm paths:")
    for path in possible_npm_paths:
        logger.error(f"  - {path}")

    # Suggest solutions
    logger.error("\nPossible solutions:")
    logger.error("1. Ensure Node.js and npm are installed and in your PATH")
    logger.error("2. Try running the script with the full path to Node.js/npm")
    logger.error("3. Try running the script outside of a virtual environment")
    logger.error("4. Check if your Node.js installation is corrupted")

    return False, None, None


def install_dependencies(app_dir, npm_path="npm", verbose=False):
    """Install npm dependencies."""
    logger.info("Installing npm dependencies...")

    npm_cmd = [npm_path, "install"]
    if not verbose:
        npm_cmd.append("--quiet")

    try:
        subprocess.run(npm_cmd, cwd=app_dir, check=True)
        logger.info("Dependencies installed successfully.")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def build_app(app_dir, mode="production", npm_path="npm", verbose=False):
    """Build the React app."""
    logger.info(f"Building React app in {mode} mode...")

    # Determine the build command based on mode
    if mode == "production":
        build_cmd = [npm_path, "run", "build"]
    else:  # development
        build_cmd = [npm_path, "run", "build:dev"]

    if not verbose:
        build_cmd.append("--quiet")

    try:
        subprocess.run(build_cmd, cwd=app_dir, check=True)
        logger.info(f"React app built successfully in {mode} mode.")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to build React app: {e}")
        return False


def copy_build_output(app_dir, output_dir, max_retries=3):
    """Copy the build output to the specified directory."""
    build_dir = os.path.join(app_dir, "dist")

    if not os.path.exists(build_dir):
        logger.error(f"Build directory not found: {build_dir}")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Try multiple times with increasing delays
    for attempt in range(max_retries):
        try:
            # If this isn't the first attempt, wait before retrying
            if attempt > 0:
                delay = 2**attempt  # Exponential backoff: 1, 2, 4 seconds
                logger.info(
                    f"Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})..."
                )
                import time

                time.sleep(delay)

            logger.info(f"Cleaning output directory: {output_dir}")

            # First try to remove the entire output directory and recreate it
            try:
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
                os.makedirs(output_dir, exist_ok=True)
            except PermissionError:
                logger.warning(
                    "Could not remove entire directory, will try to remove individual files"
                )
                # If that fails, try to remove individual files
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except PermissionError:
                        logger.warning(
                            f"Could not remove {item_path}, will try to overwrite"
                        )

            logger.info(f"Copying files from {build_dir} to {output_dir}")

            # Copy all files from build directory to output directory
            for item in os.listdir(build_dir):
                src = os.path.join(build_dir, item)
                dst = os.path.join(output_dir, item)

                if os.path.isdir(src):
                    if os.path.exists(dst):
                        try:
                            shutil.rmtree(dst)
                            shutil.copytree(src, dst)
                        except (PermissionError, OSError) as e:
                            logger.warning(
                                f"Could not remove directory {dst}, will try to copy files individually: {e}"
                            )
                            # If we can't remove the directory, try to copy files individually
                            for item_name in os.listdir(src):
                                s = os.path.join(src, item_name)
                                d = os.path.join(dst, item_name)
                                try:
                                    if os.path.isdir(s):
                                        if os.path.exists(d):
                                            try:
                                                shutil.rmtree(d)
                                            except (PermissionError, OSError):
                                                logger.warning(
                                                    f"Could not remove {d}, skipping"
                                                )
                                                continue
                                        shutil.copytree(s, d)
                                    else:
                                        shutil.copy2(s, d)
                                except (PermissionError, OSError) as e:
                                    logger.warning(f"Could not copy {s} to {d}: {e}")
                    else:
                        shutil.copytree(src, dst)
                else:
                    try:
                        shutil.copy2(src, dst)
                    except (PermissionError, OSError) as e:
                        logger.warning(f"Could not copy file {src} to {dst}: {e}")

            logger.info(f"Build output copied to {output_dir}")
            return True

        except PermissionError as e:
            logger.error(
                f"Permission error copying files (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt == max_retries - 1:
                logger.error("\nSuggestions to resolve permission issues:")
                logger.error(
                    "1. Close any applications that might be using files in the output directory"
                )
                logger.error("2. Run the script with administrator privileges")
                logger.error(
                    "3. Specify a different output directory with --output-dir"
                )
                logger.error(f"4. Manually delete the directory: {output_dir}")
                return False

        except Exception as e:
            logger.error(
                f"Failed to copy build output (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt == max_retries - 1:
                return False

    return False


def start_dev_server(app_dir, npm_path="npm", verbose=False):
    """Start the development server."""
    logger.info("Starting development server...")

    dev_cmd = [npm_path, "run", "dev"]
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
    parser.add_argument(
        "--node-path",
        help="Specify the path to the Node.js executable",
    )
    parser.add_argument(
        "--npm-path",
        help="Specify the path to the npm executable",
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

    # Use command-line specified paths if provided
    if args.node_path and args.npm_path:
        logger.info(f"Using specified Node.js path: {args.node_path}")
        logger.info(f"Using specified npm path: {args.npm_path}")
        node_path = args.node_path
        npm_path = args.npm_path

        # Verify the specified paths work
        try:
            node_version = subprocess.run(
                [node_path, "--version"], capture_output=True, text=True, check=True
            )
            npm_version = subprocess.run(
                [npm_path, "--version"], capture_output=True, text=True, check=True
            )
            logger.info(f"Node.js version: {node_version.stdout.strip()}")
            logger.info(f"npm version: {npm_version.stdout.strip()}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Error using specified paths: {e}")
            logger.error("Please check the paths and try again.")
            return 1
    else:
        # Auto-detect Node.js and npm
        node_npm_check, node_path, npm_path = check_node_npm()
        if not node_npm_check:
            logger.error(
                "You can specify paths with --node-path and --npm-path options."
            )
            return 1

    # Check if the React app directory exists
    if not os.path.exists(app_dir):
        logger.error(f"React app directory not found: {app_dir}")
        return 1

    # Install dependencies if not skipped
    if not args.skip_install:
        if not install_dependencies(app_dir, npm_path, args.verbose):
            return 1
    else:
        logger.info("Skipping dependency installation.")

    # Handle development mode
    if args.mode == "development":
        logger.info("Starting development server...")
        return 0 if start_dev_server(app_dir, npm_path, args.verbose) else 1

    # Handle production mode
    if not build_app(app_dir, args.mode, npm_path, args.verbose):
        return 1

    if not copy_build_output(app_dir, output_dir):
        return 1

    logger.info(f"Summary Chapter React app built successfully in {args.mode} mode.")
    logger.info(f"The app is available at: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
