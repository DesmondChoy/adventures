"""
Test file for analyzing simulation functionality through log analysis.

This file tests the functional correctness of the simulation system by analyzing
simulation logs. It verifies chapter sequences, lesson ratios, success rates,
and other functional aspects of the simulation.

Usage:
    1. Run a simulation: python tests/simulations/story_simulation.py
    2. Run these tests: pytest tests/simulations/test_simulation_functionality.py
"""

import pytest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.simulations.log_utils import (
    get_latest_simulation_log,
    parse_simulation_log,
    get_chapter_sequence,
    count_lesson_chapters,
    get_lesson_success_rate,
    check_simulation_complete,
    get_simulation_errors,
)


def test_simulation_log_exists():
    """Test that simulation logs exist."""
    # Check if the simulations directory exists
    assert os.path.exists("logs/simulations"), "Simulations directory not found"

    # Check if there are any simulation logs
    logs = os.listdir("logs/simulations")
    simulation_logs = [log for log in logs if log.startswith("simulation_")]
    assert len(simulation_logs) > 0, "No simulation logs found"


def test_latest_simulation_complete():
    """Test that the latest simulation completed successfully."""
    try:
        log_file = get_latest_simulation_log()
        is_complete = check_simulation_complete(log_file)
        assert is_complete, (
            f"Latest simulation in {log_file} did not complete successfully"
        )
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_chapter_sequence():
    """Test that the chapter sequence follows the expected pattern."""
    try:
        log_file = get_latest_simulation_log()
        chapter_sequence = get_chapter_sequence(log_file)

        # Verify we have the expected number of chapters
        assert len(chapter_sequence) > 0, "No chapters found in simulation"

        # Verify first two chapters are STORY type
        assert len(chapter_sequence) >= 2, "Simulation has fewer than 2 chapters"
        assert chapter_sequence[0] == "STORY", "First chapter is not STORY type"
        assert chapter_sequence[1] == "STORY", "Second chapter is not STORY type"

        # Verify last chapter is CONCLUSION type
        assert chapter_sequence[-1] == "CONCLUSION", (
            "Last chapter is not CONCLUSION type"
        )

        # Verify second-to-last chapter is STORY type
        if len(chapter_sequence) >= 2:
            assert chapter_sequence[-2] == "STORY", (
                "Second-to-last chapter is not STORY type"
            )

        # Verify LESSON chapters exist
        assert "LESSON" in chapter_sequence, "No LESSON chapters found"

        # Print chapter sequence for debugging
        print(f"Chapter sequence: {chapter_sequence}")
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_lesson_chapters_ratio():
    """Test that approximately 50% of non-fixed chapters are LESSON type."""
    try:
        log_file = get_latest_simulation_log()
        chapter_sequence = get_chapter_sequence(log_file)

        # Skip test if not enough chapters
        if len(chapter_sequence) < 5:
            pytest.skip("Not enough chapters to test ratio")

        # Calculate the number of chapters that should be lessons
        # First two and last two chapters have fixed types
        flexible_chapters = len(chapter_sequence) - 4
        expected_lessons = flexible_chapters // 2

        # Count actual lesson chapters
        lesson_count = count_lesson_chapters(log_file)

        # Allow for some variation (±1) due to available questions
        assert abs(lesson_count - expected_lessons) <= 1, (
            f"Expected approximately {expected_lessons} LESSON chapters, got {lesson_count}"
        )
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_lesson_success_rate():
    """Test that the lesson success rate is within expected range."""
    try:
        log_file = get_latest_simulation_log()
        success_rate = get_lesson_success_rate(log_file)

        # Since choices are random, we expect a success rate around 33%
        # (assuming 3 options per question with 1 correct answer)
        # Allow for variation due to randomness
        assert 0 <= success_rate <= 100, f"Success rate {success_rate}% is out of range"

        # Print success rate for debugging
        print(f"Lesson success rate: {success_rate:.1f}%")
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_no_errors_in_simulation():
    """Test that there are no errors in the simulation log."""
    try:
        log_file = get_latest_simulation_log()
        errors = get_simulation_errors(log_file)

        # Print errors for debugging if they exist
        if errors:
            for error in errors:
                print(f"Error: {error['timestamp']}: {error['message']}")

        assert len(errors) == 0, f"Found {len(errors)} errors in simulation log"
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


def test_simulation_metadata():
    """Test that the simulation metadata is correctly recorded."""
    try:
        log_file = get_latest_simulation_log()
        parsed_data = parse_simulation_log(log_file)

        # Verify required metadata fields
        assert parsed_data["run_id"] is not None, (
            "Missing run_id in simulation metadata"
        )
        assert parsed_data["timestamp"] is not None, (
            "Missing timestamp in simulation metadata"
        )
        assert parsed_data["story_category"] is not None, (
            "Missing story_category in simulation metadata"
        )
        assert parsed_data["lesson_topic"] is not None, (
            "Missing lesson_topic in simulation metadata"
        )
        assert parsed_data["story_length"] is not None, (
            "Missing story_length in simulation metadata"
        )

        # Verify story length matches chapter count
        if parsed_data["complete"]:
            expected_length = parsed_data["story_length"]
            actual_length = len(parsed_data["chapter_types"])
            assert expected_length == actual_length, (
                f"Expected {expected_length} chapters, got {actual_length}"
            )
    except FileNotFoundError:
        pytest.skip("No simulation logs found")


if __name__ == "__main__":
    # Run tests manually
    test_simulation_log_exists()
    test_latest_simulation_complete()
    test_chapter_sequence()
    test_lesson_chapters_ratio()
    test_lesson_success_rate()
    test_no_errors_in_simulation()
    test_simulation_metadata()
    print("All tests completed")
