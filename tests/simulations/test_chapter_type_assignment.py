"""
Tests for validating chapter type assignment in story simulations.

This module contains tests that verify the chapter type assignment logic
is working correctly and consistently throughout the simulation.
"""

import os
import pytest
import re
from typing import List, Tuple

from tests.simulations.log_utils import (
    get_latest_simulation_log,
    get_final_chapter_sequence,
    get_chapter_sequence,
)


def test_chapter_type_assignment_consistency():
    """
    Test that the chapter types assigned by ChapterManager.determine_chapter_types()
    are consistent with the actual chapter types used in the simulation.

    This test verifies that:
    1. The Final Chapter Sequence is present in the logs
    2. The actual chapter types match the planned sequence
    3. The first two chapters are STORY
    4. The second-to-last chapter is STORY
    5. The last chapter is CONCLUSION
    """
    # Get the latest simulation log
    log_file = get_latest_simulation_log()
    assert os.path.exists(log_file), f"Log file {log_file} does not exist"

    # Get the Final Chapter Sequence from the log
    total_chapters, final_sequence = get_final_chapter_sequence(log_file)
    assert total_chapters is not None, "Total chapters not found in log"
    assert final_sequence is not None, "Final Chapter Sequence not found in log"

    # Get the actual chapter sequence from the simulation
    actual_sequence = get_chapter_sequence(log_file)

    # Verify the sequences match
    assert len(actual_sequence) == len(final_sequence), (
        f"Sequence length mismatch: actual={len(actual_sequence)}, "
        f"planned={len(final_sequence)}"
    )

    for i, (actual, planned) in enumerate(zip(actual_sequence, final_sequence)):
        assert actual == planned, (
            f"Chapter {i + 1} type mismatch: actual={actual}, planned={planned}"
        )

    # Verify specific chapter type requirements
    assert final_sequence[0] == "STORY", (
        f"First chapter should be STORY, got {final_sequence[0]}"
    )
    assert final_sequence[1] == "STORY", (
        f"Second chapter should be STORY, got {final_sequence[1]}"
    )
    assert final_sequence[-2] == "STORY", (
        f"Second-to-last chapter should be STORY, got {final_sequence[-2]}"
    )
    assert final_sequence[-1] == "CONCLUSION", (
        f"Last chapter should be CONCLUSION, got {final_sequence[-1]}"
    )

    # Verify lesson distribution (50% of non-conclusion chapters)
    non_conclusion_count = total_chapters - 1
    required_lessons = non_conclusion_count // 2
    actual_lessons = final_sequence.count("LESSON")

    # The actual lesson count might be less than required if there aren't enough questions
    assert actual_lessons <= required_lessons, (
        f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
    )


def test_chapter_type_assignment_rules():
    """
    Test that the chapter type assignment follows the rules defined in ChapterManager.determine_chapter_types().

    Rules:
    1. First two chapters are STORY
    2. Second-to-last chapter is STORY
    3. Last chapter is CONCLUSION
    4. 50% of non-conclusion chapters should be LESSON (or less if not enough questions)
    5. LESSON chapters should be distributed between chapters 3 and second-to-last-1
    """
    # Get the latest simulation log
    log_file = get_latest_simulation_log()

    # Get the Final Chapter Sequence from the log
    total_chapters, final_sequence = get_final_chapter_sequence(log_file)
    assert total_chapters is not None, "Total chapters not found in log"
    assert final_sequence is not None, "Final Chapter Sequence not found in log"

    # Rule 1: First two chapters are STORY
    assert final_sequence[0] == "STORY", (
        f"First chapter should be STORY, got {final_sequence[0]}"
    )
    assert final_sequence[1] == "STORY", (
        f"Second chapter should be STORY, got {final_sequence[1]}"
    )

    # Rule 2 & 3: Second-to-last is STORY, last is CONCLUSION
    assert final_sequence[-2] == "STORY", (
        f"Second-to-last chapter should be STORY, got {final_sequence[-2]}"
    )
    assert final_sequence[-1] == "CONCLUSION", (
        f"Last chapter should be CONCLUSION, got {final_sequence[-1]}"
    )

    # Rule 4: 50% of non-conclusion chapters should be LESSON (or less)
    non_conclusion_count = total_chapters - 1
    required_lessons = non_conclusion_count // 2
    actual_lessons = final_sequence.count("LESSON")
    assert actual_lessons <= required_lessons, (
        f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
    )

    # Rule 5: LESSON chapters should be distributed between chapters 3 and second-to-last-1
    lesson_positions = [
        i for i, chapter_type in enumerate(final_sequence) if chapter_type == "LESSON"
    ]
    for pos in lesson_positions:
        assert 2 <= pos < len(final_sequence) - 2, (
            f"LESSON chapter at invalid position {pos + 1}"
        )


def test_extract_chapter_manager_logic():
    """
    Test that extracts and validates the chapter type assignment logic from the log file.

    This test parses the log to find the actual implementation of ChapterManager.determine_chapter_types()
    and verifies that it matches the expected rules.
    """
    # Get the latest simulation log
    log_file = get_latest_simulation_log()

    with open(log_file, "r") as f:
        log_content = f.read()

        # Look for the Final Chapter Sequence log entry
        match = re.search(
            r"Final Chapter Sequence \((\d+) total\):\s*\[(.*?)\]", log_content
        )

        assert match, "Final Chapter Sequence not found in log"

        total_chapters = int(match.group(1))
        chapter_sequence = [ct.strip() for ct in match.group(2).split(",")]

        # Verify the sequence follows the rules
        assert chapter_sequence[0] == "STORY", (
            f"First chapter should be STORY, got {chapter_sequence[0]}"
        )
        assert chapter_sequence[1] == "STORY", (
            f"Second chapter should be STORY, got {chapter_sequence[1]}"
        )
        assert chapter_sequence[-2] == "STORY", (
            f"Second-to-last chapter should be STORY, got {chapter_sequence[-2]}"
        )
        assert chapter_sequence[-1] == "CONCLUSION", (
            f"Last chapter should be CONCLUSION, got {chapter_sequence[-1]}"
        )

        # Verify lesson distribution
        non_conclusion_count = total_chapters - 1
        required_lessons = non_conclusion_count // 2
        actual_lessons = chapter_sequence.count("LESSON")

        assert actual_lessons <= required_lessons, (
            f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
        )

        # Verify LESSON chapters are in valid positions
        lesson_positions = [
            i
            for i, chapter_type in enumerate(chapter_sequence)
            if chapter_type == "LESSON"
        ]
        for pos in lesson_positions:
            assert 2 <= pos < len(chapter_sequence) - 2, (
                f"LESSON chapter at invalid position {pos + 1}"
            )


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
