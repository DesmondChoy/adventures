"""
Test the generation of adventure summaries for the React app.

This script tests the generation of adventure summaries from a simulation state file
without building the React app or starting the server.

Usage:
    python tests/test_summary_generation.py [--state-file STATE_FILE]

Options:
    --state-file STATE_FILE  Path to the simulation state file to use
"""

import os
import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_summary_generation")

# Import necessary functions
from tests.simulations.generate_chapter_summaries import find_latest_simulation_state
from tests.simulations.generate_chapter_summaries_react import (
    generate_react_summary_data,
)


async def test_summary_generation(state_file, output_file):
    """Test the generation of adventure summaries."""
    try:
        # Generate the summary data
        await generate_react_summary_data(state_file, output_file)

        # Verify the output file exists
        if not os.path.exists(output_file):
            logger.error(f"Output file not created: {output_file}")
            return False

        # Load and validate the output file
        with open(output_file, "r") as f:
            data = json.load(f)

        # Check for required fields
        required_fields = ["chapterSummaries", "educationalQuestions", "statistics"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Required field missing in output: {field}")
                return False

        # Check chapter summaries
        if not data["chapterSummaries"]:
            logger.error("No chapter summaries found in output")
            return False

        # Print summary statistics
        logger.info(f"Generated {len(data['chapterSummaries'])} chapter summaries")
        logger.info(f"Found {len(data['educationalQuestions'])} educational questions")
        logger.info(f"Statistics: {data['statistics']}")

        # Print the first chapter summary as a sample
        if data["chapterSummaries"]:
            first_chapter = data["chapterSummaries"][0]
            logger.info("\nSample Chapter Summary:")
            logger.info(f"Chapter {first_chapter['number']}: {first_chapter['title']}")
            logger.info(f"Type: {first_chapter['chapterType']}")
            logger.info(f"Summary: {first_chapter['summary'][:100]}...")

        return True
    except Exception as e:
        logger.error(f"Error testing summary generation: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function to test summary generation."""
    parser = argparse.ArgumentParser(description="Test adventure summary generation.")
    parser.add_argument(
        "--state-file",
        help="Path to the simulation state file to use",
    )
    parser.add_argument(
        "--output",
        default="test_adventure_summary.json",
        help="Output file path",
    )
    args = parser.parse_args()

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

    # Run the test
    if asyncio.run(test_summary_generation(state_file, args.output)):
        logger.info("Summary generation test passed!")
        return 0
    else:
        logger.error("Summary generation test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
