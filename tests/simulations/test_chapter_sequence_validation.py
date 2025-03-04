"""
Test file for validating chapter sequence in simulations.

This file tests that the Final Chapter Sequence generated by the ChapterManager
matches the actual chapter types assigned during the simulation.

Usage:
    1. Run a simulation: python tests/simulations/story_simulation.py
    2. Run these tests: pytest tests/simulations/test_chapter_sequence_validation.py
"""

import pytest
import os
import sys
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.simulations.log_utils import (
    get_latest_simulation_log,
    get_chapter_sequence,
    get_final_chapter_sequence,
)


def test_final_chapter_sequence_exists():
    """
    Test that the Final Chapter Sequence is captured in the logs.

    This test verifies:
    - The Final Chapter Sequence log entry exists
    - It contains a valid number of chapters
    - It contains a valid sequence of chapter types

    Skip Conditions:
    - This test is skipped when no simulation logs are found.

    If this test fails:
    - Check if the ChapterManager is correctly logging the Final Chapter Sequence
    - Verify that the log format matches the expected pattern
    """
    try:
        log_file = get_latest_simulation_log()

        # Extract the Final Chapter Sequence
        total_chapters, chapter_sequence = get_final_chapter_sequence(log_file)

        # Verify the Final Chapter Sequence exists
        assert total_chapters is not None, "Final Chapter Sequence not found in logs"
        assert chapter_sequence is not None, "Final Chapter Sequence not found in logs"

        # Verify the number of chapters
        assert total_chapters > 0, (
            "Invalid number of chapters in Final Chapter Sequence"
        )
        assert len(chapter_sequence) == total_chapters, (
            "Chapter count mismatch in Final Chapter Sequence"
        )

        # Verify the chapter types are valid
        valid_chapter_types = {"STORY", "LESSON", "CONCLUSION", "REFLECT"}
        for chapter_type in chapter_sequence:
            assert chapter_type in valid_chapter_types, (
                f"Invalid chapter type: {chapter_type}"
            )

        # Print the Final Chapter Sequence for debugging
        print(
            f"Final Chapter Sequence ({total_chapters} total): [{', '.join(chapter_sequence)}]"
        )

    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_final_sequence_matches_actual_chapters():
    """
    Test that the Final Chapter Sequence matches the actual chapter types assigned.

    This test verifies:
    - The Final Chapter Sequence matches the actual chapter types assigned
    - The number of chapters in the Final Chapter Sequence matches the actual number

    Skip Conditions:
    - This test is skipped when no simulation logs are found.
    - This test is skipped when the Final Chapter Sequence is not found.

    If this test fails:
    - Check if the ChapterManager is correctly logging the Final Chapter Sequence
    - Verify that the chapter types are being correctly assigned
    - Check for discrepancies between planned and actual chapter types
    """
    try:
        log_file = get_latest_simulation_log()

        # Extract the Final Chapter Sequence
        total_chapters, final_sequence = get_final_chapter_sequence(log_file)

        # Skip if the Final Chapter Sequence is not found
        if total_chapters is None or final_sequence is None:
            pytest.skip("Final Chapter Sequence not found in logs")

        # Extract the actual chapter sequence
        actual_sequence = get_chapter_sequence(log_file)

        # Verify the number of chapters matches
        assert len(actual_sequence) == total_chapters, (
            f"Chapter count mismatch: Final Sequence has {total_chapters} chapters, "
            f"but actual sequence has {len(actual_sequence)}"
        )

        # Verify the chapter types match
        for i, (final, actual) in enumerate(zip(final_sequence, actual_sequence)):
            assert final == actual, (
                f"Chapter type mismatch at position {i}: "
                f"Final Sequence has {final}, but actual sequence has {actual}"
            )

        # Print both sequences for debugging
        print(f"Final Chapter Sequence: [{', '.join(final_sequence)}]")
        print(f"Actual Chapter Sequence: [{', '.join(actual_sequence)}]")

    except FileNotFoundError:
        pytest.skip("No simulation logs found")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
