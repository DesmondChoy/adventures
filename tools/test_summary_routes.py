#!/usr/bin/env python3
"""
Test script for verifying the Summary Chapter routes.

This script checks if the routes for the Summary Chapter are correctly configured
and if the static assets are being served correctly.

Usage:
    python tools/test_summary_routes.py [--base-url BASE_URL]

Options:
    --base-url  Base URL of the application (default: http://localhost:8000)
"""

import argparse
import requests
import sys
import logging
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("test_summary_routes")


def test_route(base_url, route, expected_status=200, description=None):
    """Test a route and return True if it's accessible."""
    url = urljoin(base_url, route)
    try:
        response = requests.get(url)
        status = response.status_code
        if status == expected_status:
            logger.info(f"✅ {description or route}: OK ({status})")
            return True
        else:
            logger.error(
                f"❌ {description or route}: Failed (Expected {expected_status}, got {status})"
            )
            return False
    except requests.RequestException as e:
        logger.error(f"❌ {description or route}: Error - {str(e)}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Summary Chapter routes.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the application (default: http://localhost:8000)",
    )

    args = parser.parse_args()
    base_url = args.base_url

    logger.info(f"Testing Summary Chapter routes at {base_url}")

    # Test routes
    routes_to_test = [
        # Main routes
        ("/adventure/summary", 200, "Summary page"),
        (
            "/adventure/api/adventure-summary",
            404,
            "Summary API (expected 404 if no active adventure)",
        ),
        # Static assets
        ("/adventure/assets/index-placeholder.css", 200, "CSS asset"),
        ("/adventure/assets/index-placeholder.js", 200, "JS asset"),
        # Test routes
        ("/adventure/test-plain", 200, "Test plain text route"),
        ("/adventure/test-text", 200, "Test text route"),
    ]

    success_count = 0
    total_count = len(routes_to_test)

    for route, expected_status, description in routes_to_test:
        if test_route(base_url, route, expected_status, description):
            success_count += 1

    logger.info(f"Test results: {success_count}/{total_count} routes passed")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
