"""
Generate Test State Utility

This module provides utilities to generate realistic test states for the Learning Odyssey app
by leveraging the generate_all_chapters.py simulation script.

By default, this runs the actual simulation to generate a realistic state.
The mock option is only provided as a fallback for when the simulation fails
or for very quick testing where accuracy is less important.

Usage:
    from tests.utils.generate_test_state import generate_test_state

    # Generate a realistic test state with default settings (runs actual simulation)
    test_state = await generate_test_state()

    # Generate a realistic test state with specific settings
    test_state = await generate_test_state(
        story_category="enchanted_forest_tales",
        lesson_topic="Singapore History",
        output_file="tests/data/test_state.json"
    )

    # Generate a mock state for quick testing (not recommended for normal use)
    test_state = await generate_test_state(use_mock=True)
"""

import asyncio
import json
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the generate_all_chapters function
from tests.simulations.generate_all_chapters import generate_all_chapters

# Configure logging
logger = logging.getLogger("generate_test_state")


async def generate_test_state(
    story_category: Optional[str] = None,
    lesson_topic: Optional[str] = None,
    output_file: Optional[str] = None,
    use_mock: bool = False,
) -> Dict[str, Any]:
    """Generate a realistic test state using generate_all_chapters.py

    This function runs the actual simulation by default to generate a realistic state.
    The mock option should only be used as a fallback or for very quick testing.

    Args:
        story_category: Optional story category to use
        lesson_topic: Optional lesson topic to use
        output_file: Optional file path to save the state to
        use_mock: If True, return a mock state instead of running the simulation (not recommended)

    Returns:
        A dictionary containing the generated state
    """
    # Track the source of the state for debugging
    state_source = "unknown"

    if use_mock:
        logger.warning(
            "Using mock state instead of running simulation - this is not recommended for normal testing"
        )
        state_source = "mock:hardcoded"
        return await _create_mock_state(story_category, lesson_topic)

    try:
        logger.info(
            f"Generating realistic test state with category={story_category}, topic={lesson_topic}"
        )
        state_source = "realistic:generate_all_chapters"

        # Generate the state using generate_all_chapters
        state = await generate_all_chapters(story_category, lesson_topic)

        if state is None:
            logger.error("Failed to generate state using simulation")
            logger.warning("Falling back to mock state - results may not be accurate")
            state_source = "mock:fallback"
            return await _create_mock_state(story_category, lesson_topic)

        # Convert the state to a dictionary if it's not already
        if hasattr(state, "dict"):
            state_dict = state.dict()
        else:
            state_dict = state

        # Add source information to metadata for debugging
        if "metadata" not in state_dict:
            state_dict["metadata"] = {}
        if "simulation" not in state_dict["metadata"]:
            state_dict["metadata"]["simulation"] = {}

        state_dict["metadata"]["simulation"]["state_source"] = state_source
        state_dict["metadata"]["simulation"]["generation_timestamp"] = (
            datetime.now().isoformat()
        )

        # Save to file if specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(state_dict, f, indent=2)
            logger.info(f"Saved state to {output_file}")

        logger.info(
            f"Successfully generated realistic test state (source: {state_source})"
        )
        return state_dict

    except Exception as e:
        logger.error(f"Error generating test state: {e}")
        import traceback

        traceback.print_exc()

        # Return a mock state as fallback
        logger.warning(
            "Falling back to mock state due to error - results may not be accurate"
        )
        state_source = "mock:error_fallback"
        mock_state = await _create_mock_state(story_category, lesson_topic)

        # Add error information to metadata
        if "metadata" not in mock_state:
            mock_state["metadata"] = {}
        if "simulation" not in mock_state["metadata"]:
            mock_state["metadata"]["simulation"] = {}

        mock_state["metadata"]["simulation"]["state_source"] = state_source
        mock_state["metadata"]["simulation"]["error"] = str(e)
        mock_state["metadata"]["simulation"]["generation_timestamp"] = (
            datetime.now().isoformat()
        )

        return mock_state


async def _create_mock_state(
    story_category: Optional[str] = None, lesson_topic: Optional[str] = None
) -> Dict[str, Any]:
    """Create a mock state for testing when simulation fails or for quick tests

    This creates a synthetic state with hardcoded values. It should only be used
    as a fallback when the simulation fails or for very quick testing where
    accuracy is less important.

    Args:
        story_category: Optional story category to use
        lesson_topic: Optional lesson topic to use

    Returns:
        A dictionary containing a mock state
    """
    story_category = story_category or "enchanted_forest_tales"
    lesson_topic = lesson_topic or "Singapore History"

    # Generate a unique run ID and timestamp
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    logger.info(f"Creating mock state with run_id={run_id}")

    # Create a basic mock state
    mock_state = {
        "current_chapter_id": "chapter_10",
        "story_length": 10,
        "selected_narrative_elements": {
            "settings": "Enchanted Forest",
            "characters": "Brave Knight",
            "objects": "Magic Sword",
            "events": "Dragon Attack",
        },
        "selected_sensory_details": {
            "visuals": "Sparkling lights",
            "sounds": "Rustling leaves",
            "smells": "Fresh pine",
            "textures": "Rough bark",
        },
        "selected_theme": "Friendship",
        "selected_moral_teaching": "Honesty is the best policy",
        "selected_plot_twist": "The forest guardian was the old friend all along",
        "current_storytelling_phase": "Conclusion",
        "chapters": [
            {
                "chapter_number": i,
                "chapter_type": "story"
                if i % 2 == 1
                else "lesson"
                if i < 9
                else "conclusion",
                "content": f"This is chapter {i}.",
                "chapter_content": {
                    "content": f"This is chapter {i}.",
                    "choices": [
                        {"text": f"Option {j + 1}", "next_chapter": f"chapter_{i}_{j}"}
                        for j in range(3)
                    ]
                    if i % 2 == 1 and i < 10
                    else [],
                },
                "question": {
                    "question": f"Test question for chapter {i}?",
                    "answers": [
                        {"text": "Correct answer", "is_correct": True},
                        {"text": "Wrong answer", "is_correct": False},
                    ],
                    "explanation": "This is the explanation.",
                }
                if i % 2 == 0 and i < 10
                else None,
            }
            for i in range(1, 11)
        ],
        "chapter_summaries": [
            f"Chapter {i}: Summary for chapter {i}." for i in range(1, 11)
        ],
        "lesson_questions": [
            {
                "question": f"Test question {i}?",
                "answers": [
                    {"text": "Correct answer", "is_correct": True},
                    {"text": "Wrong answer", "is_correct": False},
                ],
                "explanation": "This is the explanation.",
            }
            for i in range(1, 4)
        ],
        "planned_chapter_types": [
            "story",
            "lesson",
            "story",
            "lesson",
            "reflect",
            "story",
            "lesson",
            "story",
            "lesson",
            "conclusion",
        ],
        "metadata": {
            "agency": {"name": "Magic Sword", "type": "item", "references": []},
            "simulation": {
                "run_id": run_id,
                "timestamp": timestamp,
                "story_category": story_category,
                "lesson_topic": lesson_topic,
                "is_mock": True,
            },
        },
    }

    return mock_state


def load_state_from_file(file_path: str) -> Dict[str, Any]:
    """Load a state from a JSON file

    Args:
        file_path: Path to the JSON file

    Returns:
        A dictionary containing the loaded state
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading state from {file_path}: {e}")
        return {}


def compare_state_structures(
    state1: Dict[str, Any], state2: Dict[str, Any], ignore_fields: Optional[list] = None
) -> list:
    """Compare the structure of two states and report differences

    Args:
        state1: First state to compare
        state2: Second state to compare
        ignore_fields: Optional list of fields to ignore

    Returns:
        A list of differences between the states
    """
    ignore_fields = ignore_fields or []
    differences = []

    # Compare top-level fields
    for field in set(state1.keys()) | set(state2.keys()):
        if field in ignore_fields:
            continue

        if field not in state1:
            differences.append(f"Field '{field}' missing in state1")
        elif field not in state2:
            differences.append(f"Field '{field}' missing in state2")
        elif type(state1[field]) != type(state2[field]):
            differences.append(
                f"Field '{field}' has different types: {type(state1[field]).__name__} vs {type(state2[field]).__name__}"
            )

    # Compare chapters structure if present in both states
    if "chapters" in state1 and "chapters" in state2:
        # Check chapter count
        if len(state1["chapters"]) != len(state2["chapters"]):
            differences.append(
                f"Different chapter count: {len(state1['chapters'])} vs {len(state2['chapters'])}"
            )

        # Check chapter structure for common chapters
        min_chapters = min(len(state1["chapters"]), len(state2["chapters"]))
        for i in range(min_chapters):
            ch1 = state1["chapters"][i]
            ch2 = state2["chapters"][i]

            # Compare chapter fields
            for field in set(ch1.keys()) | set(ch2.keys()):
                if field in ignore_fields:
                    continue

                if field not in ch1:
                    differences.append(
                        f"Chapter {i + 1}: Field '{field}' missing in state1"
                    )
                elif field not in ch2:
                    differences.append(
                        f"Chapter {i + 1}: Field '{field}' missing in state2"
                    )
                elif (
                    field == "chapter_type"
                    and str(ch1[field]).lower() != str(ch2[field]).lower()
                ):
                    differences.append(
                        f"Chapter {i + 1}: Different chapter_type: '{ch1[field]}' vs '{ch2[field]}'"
                    )

    return differences


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse command-line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate test state for Learning Odyssey"
    )
    parser.add_argument("--category", type=str, help="Specify story category")
    parser.add_argument("--topic", type=str, help="Specify lesson topic")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock state instead of running simulation",
    )
    args = parser.parse_args()

    # Run the generator
    asyncio.run(
        generate_test_state(
            story_category=args.category,
            lesson_topic=args.topic,
            output_file=args.output,
            use_mock=args.mock,
        )
    )
