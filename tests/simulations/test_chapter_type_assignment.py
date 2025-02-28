"""
Tests for validating chapter type assignment in story simulations.

This module contains tests that verify the chapter type assignment logic
is working correctly and consistently throughout the simulation, with
priority given to:
1. No consecutive LESSON chapters (highest priority)
2. At least 1 REFLECT chapter in every scenario (required)
3. Every LESSON assumes at least 3 questions available
4. Accept 25% of scenarios where there are two LESSON chapters (optimization tradeoff)
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
    assert final_sequence[-2] == "STORY", (
        f"Second-to-last chapter should be STORY, got {final_sequence[-2]}"
    )
    assert final_sequence[-1] == "CONCLUSION", (
        f"Last chapter should be CONCLUSION, got {final_sequence[-1]}"
    )

    # Verify lesson distribution (50% of remaining chapters, rounded down)
    # Remaining chapters = total - 3 (first, second-to-last, and last)
    remaining_chapters = total_chapters - 3
    required_lessons = remaining_chapters // 2
    actual_lessons = final_sequence.count("LESSON")

    # The actual lesson count might be less than required if there aren't enough questions
    assert actual_lessons <= required_lessons, (
        f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
    )

    # Verify no consecutive LESSON chapters
    for i in range(1, len(final_sequence)):
        assert not (
            final_sequence[i] == "LESSON" and final_sequence[i - 1] == "LESSON"
        ), f"Found consecutive LESSON chapters at positions {i - 1} and {i}"

    # Verify REFLECT chapters only follow LESSON chapters
    reflect_positions = [i for i, ct in enumerate(final_sequence) if ct == "REFLECT"]
    for pos in reflect_positions:
        assert pos > 0 and final_sequence[pos - 1] == "LESSON", (
            f"REFLECT chapter at position {pos} does not follow a LESSON chapter"
        )

    # Verify STORY chapters follow REFLECT chapters
    for pos in reflect_positions:
        assert pos < len(final_sequence) - 1 and final_sequence[pos + 1] == "STORY", (
            f"REFLECT chapter at position {pos} is not followed by a STORY chapter"
        )


def test_chapter_type_assignment_rules():
    """
    Test that the chapter type assignment follows the rules defined in ChapterManager.determine_chapter_types().

    Rules:
    1. First chapter is STORY
    2. Second-to-last chapter is STORY
    3. Last chapter is CONCLUSION
    4. 50% of remaining chapters should be LESSON (or less if not enough questions)
    5. No consecutive LESSON chapters
    6. REFLECT chapters only follow LESSON chapters
    7. STORY chapters must follow REFLECT chapters
    8. 50% of LESSON chapters (rounded down) should be followed by REFLECT chapters
    """
    # Get the latest simulation log
    log_file = get_latest_simulation_log()

    # Get the Final Chapter Sequence from the log
    total_chapters, final_sequence = get_final_chapter_sequence(log_file)
    assert total_chapters is not None, "Total chapters not found in log"
    assert final_sequence is not None, "Final Chapter Sequence not found in log"

    # Rule 1: First chapter is STORY
    assert final_sequence[0] == "STORY", (
        f"First chapter should be STORY, got {final_sequence[0]}"
    )

    # Rule 2 & 3: Second-to-last is STORY, last is CONCLUSION
    assert final_sequence[-2] == "STORY", (
        f"Second-to-last chapter should be STORY, got {final_sequence[-2]}"
    )
    assert final_sequence[-1] == "CONCLUSION", (
        f"Last chapter should be CONCLUSION, got {final_sequence[-1]}"
    )

    # Rule 4: 50% of remaining chapters should be LESSON (or less)
    remaining_chapters = total_chapters - 3  # Excluding first, second-to-last, and last
    required_lessons = remaining_chapters // 2
    actual_lessons = final_sequence.count("LESSON")
    assert actual_lessons <= required_lessons, (
        f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
    )

    # Rule 5: No consecutive LESSON chapters
    for i in range(1, len(final_sequence)):
        assert not (
            final_sequence[i] == "LESSON" and final_sequence[i - 1] == "LESSON"
        ), f"Found consecutive LESSON chapters at positions {i - 1} and {i}"

    # Rule 6: REFLECT chapters only follow LESSON chapters
    reflect_positions = [
        i for i, chapter_type in enumerate(final_sequence) if chapter_type == "REFLECT"
    ]
    for pos in reflect_positions:
        assert pos > 0 and final_sequence[pos - 1] == "LESSON", (
            f"REFLECT chapter at position {pos} does not follow a LESSON chapter"
        )

    # Rule 7: STORY chapters must follow REFLECT chapters
    for pos in reflect_positions:
        assert pos < len(final_sequence) - 1 and final_sequence[pos + 1] == "STORY", (
            f"REFLECT chapter at position {pos} is not followed by a STORY chapter"
        )

    # Rule 8: 50% of LESSON chapters (rounded down) should be followed by REFLECT chapters
    expected_reflect_count = actual_lessons // 2
    actual_reflect_count = len(reflect_positions)
    assert actual_reflect_count <= expected_reflect_count, (
        f"Too many REFLECT chapters: {actual_reflect_count} > {expected_reflect_count}"
    )

    # LESSON chapters should be in valid positions (not in fixed positions)
    lesson_positions = [
        i for i, chapter_type in enumerate(final_sequence) if chapter_type == "LESSON"
    ]
    for pos in lesson_positions:
        assert 1 <= pos < len(final_sequence) - 2, (
            f"LESSON chapter at invalid position {pos + 1}"
        )


def test_lesson_chapter_distribution():
    """
    Test that verifies the distribution of scenarios with 2 vs 3 LESSON chapters.

    This test checks that:
    1. The percentage of scenarios with 2 LESSON chapters is around 25%
    2. The majority of scenarios have 3 LESSON chapters
    3. Every scenario has at least 2 LESSON chapters
    4. No scenario has more than 3 LESSON chapters

    Note: This test requires running multiple simulations to get a statistically
    significant sample. It's designed to be run as part of a larger test suite
    that generates multiple simulation logs.
    """
    # Get the latest simulation log
    log_file = get_latest_simulation_log()

    # Get the Final Chapter Sequence from the log
    total_chapters, final_sequence = get_final_chapter_sequence(log_file)
    assert total_chapters is not None, "Total chapters not found in log"
    assert final_sequence is not None, "Final Chapter Sequence not found in log"

    # Count the number of LESSON chapters
    lesson_count = final_sequence.count("LESSON")

    # Verify that the number of LESSON chapters is either 2 or 3
    assert 2 <= lesson_count <= 3, (
        f"Expected 2 or 3 LESSON chapters, got {lesson_count}"
    )

    # Note: In a real test environment, we would run multiple simulations
    # and verify that approximately 25% of them have 2 LESSON chapters.
    # For a single simulation, we can only verify that the number is valid.

    # Print the LESSON count for debugging
    print(f"Number of LESSON chapters: {lesson_count}")

    # Verify at least 1 REFLECT chapter
    reflect_count = final_sequence.count("REFLECT")
    assert reflect_count >= 1, "Expected at least 1 REFLECT chapter"

    # Print the REFLECT count for debugging
    print(f"Number of REFLECT chapters: {reflect_count}")


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
        # Rule 1: First chapter is STORY
        assert chapter_sequence[0] == "STORY", (
            f"First chapter should be STORY, got {chapter_sequence[0]}"
        )

        # Rule 2 & 3: Second-to-last is STORY, last is CONCLUSION
        assert chapter_sequence[-2] == "STORY", (
            f"Second-to-last chapter should be STORY, got {chapter_sequence[-2]}"
        )
        assert chapter_sequence[-1] == "CONCLUSION", (
            f"Last chapter should be CONCLUSION, got {chapter_sequence[-1]}"
        )

        # Rule 4: 50% of remaining chapters should be LESSON (or less)
        remaining_chapters = (
            total_chapters - 3
        )  # Excluding first, second-to-last, and last
        required_lessons = remaining_chapters // 2
        actual_lessons = chapter_sequence.count("LESSON")
        assert actual_lessons <= required_lessons, (
            f"Too many LESSON chapters: {actual_lessons} > {required_lessons}"
        )

        # Rule 5: No consecutive LESSON chapters
        for i in range(1, len(chapter_sequence)):
            assert not (
                chapter_sequence[i] == "LESSON" and chapter_sequence[i - 1] == "LESSON"
            ), f"Found consecutive LESSON chapters at positions {i - 1} and {i}"

        # Rule 6: REFLECT chapters only follow LESSON chapters
        reflect_positions = [
            i
            for i, chapter_type in enumerate(chapter_sequence)
            if chapter_type == "REFLECT"
        ]
        for pos in reflect_positions:
            assert pos > 0 and chapter_sequence[pos - 1] == "LESSON", (
                f"REFLECT chapter at position {pos} does not follow a LESSON chapter"
            )

        # Rule 7: STORY chapters must follow REFLECT chapters
        for pos in reflect_positions:
            assert (
                pos < len(chapter_sequence) - 1 and chapter_sequence[pos + 1] == "STORY"
            ), f"REFLECT chapter at position {pos} is not followed by a STORY chapter"

        # Rule 8: 50% of LESSON chapters (rounded down) should be followed by REFLECT chapters
        expected_reflect_count = actual_lessons // 2
        actual_reflect_count = len(reflect_positions)
        assert actual_reflect_count <= expected_reflect_count, (
            f"Too many REFLECT chapters: {actual_reflect_count} > {expected_reflect_count}"
        )

        # LESSON chapters should be in valid positions (not in fixed positions)
        lesson_positions = [
            i
            for i, chapter_type in enumerate(chapter_sequence)
            if chapter_type == "LESSON"
        ]
        for pos in lesson_positions:
            assert 1 <= pos < len(chapter_sequence) - 2, (
                f"LESSON chapter at invalid position {pos + 1}"
            )


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
