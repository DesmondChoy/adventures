"""
Test the generate_test_state utility

This script tests the generate_test_state utility to ensure it can generate
realistic test states for the Learning Odyssey app.
"""

import logging
from pathlib import Path

# Import the generate_test_state utility
from tests.utils.generate_test_state import (
    compare_state_structures,
    generate_test_state,
    load_state_from_file,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_generate_state")


async def test_mock_state_generation() -> None:
    """Test generating a mock state"""
    logger.info("Testing mock state generation")

    # Generate a mock state
    mock_state = await generate_test_state(use_mock=True)

    # Verify the mock state has the expected structure
    assert "current_chapter_id" in mock_state, "Missing current_chapter_id"
    assert "story_length" in mock_state, "Missing story_length"
    assert "chapters" in mock_state, "Missing chapters"
    assert len(mock_state["chapters"]) == 10, "Expected 10 chapters"
    assert "chapter_summaries" in mock_state, "Missing chapter_summaries"
    assert len(mock_state["chapter_summaries"]) == 10, "Expected 10 chapter summaries"
    assert "planned_chapter_types" in mock_state, "Missing planned_chapter_types"
    assert len(mock_state["planned_chapter_types"]) == 10, (
        "Expected 10 planned chapter types"
    )

    # Verify the last chapter is a CONCLUSION chapter
    last_chapter = mock_state["chapters"][-1]
    assert last_chapter["chapter_type"] == "conclusion", (
        "Last chapter should be CONCLUSION"
    )

    logger.info("Mock state generation test passed")


async def test_state_comparison() -> None:
    """Test comparing state structures"""
    logger.info("Testing state comparison")

    # Generate two mock states
    state1 = await generate_test_state(use_mock=True)
    state2 = await generate_test_state(use_mock=True)

    # Compare the states
    differences = compare_state_structures(state1, state2)

    # There should be some differences (like run_id, timestamp)
    logger.info(f"Found {len(differences)} differences between states")
    for diff in differences:
        logger.info(f"  - {diff}")

    # Modify state2 to introduce a structural difference
    state2["chapters"][0]["new_field"] = "test"

    # Compare again
    differences = compare_state_structures(state1, state2)

    # There should be at least one structural difference
    assert any("missing" in diff for diff in differences), (
        "Expected structural difference not found"
    )

    logger.info("State comparison test passed")


async def test_save_and_load(tmp_path: Path) -> None:
    """Test saving and loading a state"""
    logger.info("Testing save and load")

    # Save to a temporary file
    temp_file = tmp_path / "test_state.json"
    await generate_test_state(use_mock=True, output_file=str(temp_file))

    # Load the state
    loaded_state = load_state_from_file(str(temp_file))

    # Compare the loaded state with a new mock state
    differences = compare_state_structures(
        loaded_state,
        await generate_test_state(use_mock=True),
        ignore_fields=["run_id", "timestamp"],
    )

    # There should be minimal structural differences
    logger.info(f"Found {len(differences)} structural differences after save/load")
    for diff in differences:
        logger.info(f"  - {diff}")

    logger.info("Save and load test passed")
