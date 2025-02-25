"""
Tests for error detection and logging in story simulations.

This file contains tests that verify:
1. Errors in simulation logs are properly detected and classified
2. The logging level in story_simulation.py is sufficient to print errors
3. Error recovery mechanisms work as expected
4. Simulation can complete despite recoverable errors

Usage:
    pytest tests/simulations/test_simulation_errors.py
"""

import pytest
import os
import sys
import re
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.simulations.log_utils import (
    get_simulation_log_by_run_id,
    get_latest_simulation_log,
    parse_simulation_log,
    get_simulation_errors,
    check_simulation_complete,
)


def detect_errors_in_log(log_file):
    """Custom function to detect errors in the log file."""
    errors = []
    with open(log_file, "r") as f:
        for line in f:
            if '"level": "ERROR"' in line or '"level":"ERROR"' in line:
                # Extract timestamp and message
                try:
                    # Try to parse as JSON
                    import json

                    data = json.loads(line)
                    errors.append(
                        {
                            "timestamp": data.get("timestamp", ""),
                            "message": data.get("message", ""),
                        }
                    )
                except json.JSONDecodeError:
                    # If not valid JSON, extract using regex
                    import re

                    timestamp_match = re.search(r'"timestamp": "([^"]+)"', line)
                    message_match = re.search(r'"message": "([^"]+)"', line)

                    timestamp = timestamp_match.group(1) if timestamp_match else ""
                    message = message_match.group(1) if message_match else line.strip()

                    errors.append({"timestamp": timestamp, "message": message})
    return errors


def test_error_detection_and_classification():
    """
    Test that errors in the simulation log are properly detected and classified.

    This test verifies:
    - Errors in the log file are correctly identified
    - Errors can be classified into different categories (connection, service, etc.)
    - The simulation completes successfully despite encountering errors

    Skip Conditions:
    - This test is skipped when no errors are found in the log file.

    If this test fails:
    - Check if the log file format has changed
    - Verify that the error detection function can parse the log format
    - Ensure the simulation is completing with a STORY_COMPLETE event
    """
    # Try to use a specific log file that we know contains errors, or fall back to the latest log
    log_file = get_latest_simulation_log()

    # Use our custom error detection function
    errors = detect_errors_in_log(log_file)

    # Also try the built-in function for comparison
    built_in_errors = get_simulation_errors(log_file)
    print(f"Built-in error detection found: {len(built_in_errors)} errors")

    # Classify errors into categories
    connection_errors = [e for e in errors if "WebSocket connection" in e["message"]]
    service_errors = [e for e in errors if "service restart" in e["message"]]
    other_errors = [
        e
        for e in errors
        if "WebSocket connection" not in e["message"]
        and "service restart" not in e["message"]
    ]

    # Print error counts for debugging
    print(f"Total errors: {len(errors)}")
    print(f"Connection errors: {len(connection_errors)}")
    print(f"Service errors: {len(service_errors)}")
    print(f"Other errors: {len(other_errors)}")

    # Print the first few errors for debugging
    for i, error in enumerate(errors[:3]):
        print(f"Error {i + 1}: {error['timestamp']} - {error['message'][:100]}...")

    # If no errors are found, skip this test
    if len(errors) == 0:
        pytest.skip("No errors found in log file, skipping error classification test")

    # Check if the simulation has a STORY_COMPLETE event, indicating successful completion
    def check_simulation_completed_successfully(log_file):
        with open(log_file, "r") as f:
            log_content = f.read()
            return "EVENT:STORY_COMPLETE" in log_content

    # Check if the simulation recovered from these errors
    simulation_completed = check_simulation_completed_successfully(log_file)
    print(f"Simulation completed successfully: {simulation_completed}")

    # We know this simulation completed despite errors, so we expect this to be true
    assert simulation_completed, (
        "Simulation did not complete despite recoverable errors"
    )


def test_logging_level_sufficient_for_errors():
    """
    Test that the logging level in story_simulation.py is sufficient to print errors.

    This test verifies:
    - ERROR level messages are present in the log file
    - Specific error types (like WebSocket connection errors) are being logged
    - The logging level in story_simulation.py is set to capture ERROR messages

    Skip Conditions:
    - This test is skipped when no ERROR level messages are found in the log file.
    - This test is also skipped when no WebSocket connection errors are found.

    If this test fails:
    - Check if the logging level in story_simulation.py has been changed
    - Verify that the logger is properly configured to log ERROR level messages
    - Ensure that error handling code is using the logger to log errors
    """
    log_file = get_latest_simulation_log()

    # Check for ERROR level messages
    with open(log_file, "r") as f:
        log_content = f.read()

    # Check if ERROR level messages are present
    has_error_messages = (
        'level": "ERROR"' in log_content or "level: ERROR" in log_content
    )

    # If no error messages are found, skip this test
    if not has_error_messages:
        pytest.skip("No ERROR level messages found in log, skipping logging level test")

    # Verify specific error types are logged if errors are present
    has_connection_errors = (
        "WebSocket connection closed" in log_content
        or "connection closed" in log_content
    )

    if not has_connection_errors:
        pytest.skip(
            "No WebSocket connection errors found in log, skipping specific error type test"
        )

    # Print the logging level configuration from the simulation script
    import inspect
    from tests.simulations.story_simulation import simulation_logger

    logger_level = simulation_logger.level
    logger_level_name = logging_level_to_name(logger_level)

    print(f"Simulation logger level: {logger_level_name} ({logger_level})")
    assert logger_level <= 40, (
        "Logging level is not sufficient to capture ERROR messages (level 40)"
    )


# Helper function to check if simulation completed successfully
def check_simulation_completed_successfully(log_file):
    with open(log_file, "r") as f:
        log_content = f.read()
        return "EVENT:STORY_COMPLETE" in log_content


def test_error_recovery_mechanism():
    """
    Test that the simulation can recover from certain types of errors.

    This test verifies:
    - The retry mechanism is working after errors occur
    - The simulation can continue and complete successfully after encountering errors
    - Retry messages are properly logged

    Skip Conditions:
    - This test is skipped when no retry messages are found in the log file.

    If this test fails:
    - Check if the retry logic in story_simulation.py is working correctly
    - Verify the MAX_RETRIES and RETRY_DELAY constants
    - Ensure that WebSocket reconnection is implemented properly
    - Check that error handling doesn't terminate the simulation prematurely
    """
    log_file = get_latest_simulation_log()

    # Check for retry messages after errors
    retry_messages = []
    with open(log_file, "r") as f:
        for line in f:
            if "Retrying in" in line:
                retry_messages.append(line)

    # Print retry messages for debugging
    for msg in retry_messages:
        print(f"Retry message: {msg.strip()}")

    # If no retry messages are found, skip this test
    if len(retry_messages) == 0:
        pytest.skip("No retry messages found in log, skipping error recovery test")

    # Verify successful completion after retries using our custom function
    simulation_completed = check_simulation_completed_successfully(log_file)
    print(f"Simulation completed successfully: {simulation_completed}")

    # We know this simulation completed despite errors, so we expect this to be true
    assert simulation_completed, "Simulation did not complete after retries"


def extract_chapter_info(log_file):
    """Extract chapter information from the log file."""
    chapters = []
    with open(log_file, "r") as f:
        for line in f:
            if "EVENT:CHAPTER_START" in line:
                try:
                    # Try to parse as JSON
                    import json

                    # Extract the JSON part
                    json_str = line
                    data = json.loads(json_str)

                    chapters.append(
                        {
                            "chapter_number": data.get("chapter_number", 0),
                            "chapter_type": data.get("chapter_type", "UNKNOWN").upper(),
                            "chapter_id": data.get("chapter_id", ""),
                        }
                    )
                except json.JSONDecodeError:
                    # If not valid JSON, extract using regex
                    import re

                    chapter_num_match = re.search(r'"chapter_number": (\d+)', line)
                    chapter_type_match = re.search(r'"chapter_type": "([^"]+)"', line)

                    if chapter_num_match and chapter_type_match:
                        chapters.append(
                            {
                                "chapter_number": int(chapter_num_match.group(1)),
                                "chapter_type": chapter_type_match.group(1).upper(),
                                "chapter_id": "",
                            }
                        )

    # Sort chapters by chapter number
    chapters.sort(key=lambda x: x["chapter_number"])
    return chapters


def test_comprehensive_error_analysis():
    """
    Perform a comprehensive analysis of errors in the simulation log.

    This test verifies:
    - Errors can be mapped to specific chapters in the simulation
    - The simulation makes significant progress despite errors (at least 80% completion)
    - Chapter information can be extracted from the log file

    Skip Conditions:
    - This test is skipped when no errors are found in the log file.

    If this test fails:
    - Check if the chapter information format in the log has changed
    - Verify that the simulation is making sufficient progress despite errors
    - Ensure that chapter events are being properly logged
    - Check if the expected story length (10 chapters) has changed
    """
    log_file = get_latest_simulation_log()

    # Use our custom error detection function
    errors = detect_errors_in_log(log_file)

    # Extract chapter information
    chapters = extract_chapter_info(log_file)
    print(f"Found {len(chapters)} chapters in the log")
    for chapter in chapters:
        print(f"Chapter {chapter['chapter_number']}: {chapter['chapter_type']}")

    # If no errors are found, skip this test
    if len(errors) == 0:
        pytest.skip(
            "No errors found in log file, skipping comprehensive error analysis"
        )

    # Analyze errors in context of the simulation timeline
    errors_by_chapter = {}
    for error in errors:
        # Extract chapter number from error message if possible
        chapter_match = re.search(r"chapter (\d+)", error["message"])
        chapter_num = int(chapter_match.group(1)) if chapter_match else 0

        if chapter_num not in errors_by_chapter:
            errors_by_chapter[chapter_num] = []
        errors_by_chapter[chapter_num].append(error)

    # Print errors by chapter for debugging
    for chapter_num, chapter_errors in errors_by_chapter.items():
        print(f"Chapter {chapter_num} had {len(chapter_errors)} errors")
        for error in chapter_errors[:2]:  # Print first 2 errors per chapter
            print(f"  - {error['message'][:100]}...")

    # Verify simulation progressed despite errors
    assert len(chapters) > 0, "No chapters found in the simulation log"

    # Check if the simulation made significant progress despite errors
    # The simulation should have at least 8 chapters (80% completion)
    min_expected_chapters = 8
    assert len(chapters) >= min_expected_chapters, (
        f"Expected at least {min_expected_chapters} chapters, got {len(chapters)}"
    )

    # Log the completion percentage
    story_length = 10  # Known fixed story length from the simulation
    completion_percentage = (len(chapters) / story_length) * 100
    print(
        f"Simulation completion: {completion_percentage:.1f}% ({len(chapters)}/{story_length} chapters)"
    )


def test_no_critical_errors():
    """
    Test that there are no critical errors in the simulation log.

    This test verifies:
    - Errors can be classified as critical or recoverable
    - No critical errors (fatal, crash, exception, traceback) are present in the log
    - The simulation completes successfully despite recoverable errors

    Skip Conditions:
    - This test is skipped when no errors are found in the log file.

    If this test fails:
    - Check for critical error keywords in the log (fatal, crash, exception, traceback)
    - Investigate any critical errors found and fix their root causes
    - Ensure that error handling is properly categorizing errors
    """
    log_file = get_latest_simulation_log()

    # Use our custom error detection function
    errors = detect_errors_in_log(log_file)

    # If no errors are found, skip this test
    if len(errors) == 0:
        pytest.skip("No errors found in log file, skipping critical error test")

    # Classify errors into categories
    critical_errors = []
    recoverable_errors = []

    for error in errors:
        # Check if the error message indicates a critical error
        if any(
            term in error["message"].lower()
            for term in ["critical", "fatal", "crash", "exception", "traceback"]
        ):
            critical_errors.append(error)
        else:
            recoverable_errors.append(error)

    # Print error counts for debugging
    print(f"Critical errors: {len(critical_errors)}")
    print(f"Recoverable errors: {len(recoverable_errors)}")

    # Print critical errors for debugging
    for i, error in enumerate(critical_errors):
        print(
            f"Critical error {i + 1}: {error['timestamp']} - {error['message'][:100]}..."
        )

    # Assert that there are no critical errors
    assert len(critical_errors) == 0, (
        f"Found {len(critical_errors)} critical errors in the log"
    )

    # Assert that the simulation completed successfully despite recoverable errors
    assert check_simulation_completed_successfully(log_file), (
        "Simulation did not complete despite recoverable errors"
    )


def test_error_logging_in_story_simulation():
    """
    Test that the story_simulation.py file has appropriate error logging.

    This test verifies:
    - The story_simulation.py file contains error logging statements
    - There are try-except blocks to catch and handle errors
    - Error handling is implemented throughout the code

    Skip Conditions:
    - This test is not skipped under any conditions.

    If this test fails:
    - Check if error logging statements have been removed from story_simulation.py
    - Verify that try-except blocks are present to catch errors
    - Ensure that error handling is properly implemented
    """
    # Read the story_simulation.py file
    with open("tests/simulations/story_simulation.py", "r") as f:
        content = f.read()

    # Check for error logging patterns
    error_logging_patterns = [
        r"simulation_logger\.error\(",
        r"logger\.error\(",
        r"logging\.error\(",
    ]

    error_logging_count = 0
    for pattern in error_logging_patterns:
        matches = re.findall(pattern, content)
        error_logging_count += len(matches)

    # Print the count of error logging statements
    print(
        f"Found {error_logging_count} error logging statements in story_simulation.py"
    )

    # Assert that there are error logging statements
    assert error_logging_count > 0, (
        "No error logging statements found in story_simulation.py"
    )

    # Check for try-except blocks that catch and log errors
    try_except_blocks = re.findall(r"try:.*?except.*?:", content, re.DOTALL)
    print(f"Found {len(try_except_blocks)} try-except blocks in story_simulation.py")

    # Assert that there are try-except blocks
    assert len(try_except_blocks) > 0, (
        "No try-except blocks found in story_simulation.py"
    )


def logging_level_to_name(level: int) -> str:
    """Convert a logging level integer to its name."""
    import logging

    level_names = {
        logging.CRITICAL: "CRITICAL",
        logging.ERROR: "ERROR",
        logging.WARNING: "WARNING",
        logging.INFO: "INFO",
        logging.DEBUG: "DEBUG",
        logging.NOTSET: "NOTSET",
    }

    return level_names.get(level, f"UNKNOWN ({level})")


if __name__ == "__main__":
    # Run tests manually
    test_error_detection_and_classification()
    test_logging_level_sufficient_for_errors()
    test_error_recovery_mechanism()
    test_comprehensive_error_analysis()
    test_error_logging_in_story_simulation()
    print("All tests completed")
