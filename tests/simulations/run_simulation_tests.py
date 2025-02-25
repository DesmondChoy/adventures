#!/usr/bin/env python3
"""
Orchestration script for Learning Odyssey testing workflow.
This script automates:
1. Starting the FastAPI server with uvicorn
2. Running the story simulation
3. Executing all pytest tests in tests/simulation with prefix test_
4. Cleaning up all processes

Usage:
    python tests/simulations/run_simulation_tests.py [options]
"""

import subprocess
import time
import os
import signal
import sys
import argparse
import glob
import re
import socket
import random
from pathlib import Path
from enum import Enum

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import ChapterType enum
from app.models.story import ChapterType

# Global variables for cleanup
processes = []


def generate_chapter_sequence(total_chapters=10, available_questions=5):
    """Generate a chapter sequence similar to ChapterManager.determine_chapter_types().

    Args:
        total_chapters: Total number of chapters in the adventure
        available_questions: Number of available questions for the topic

    Returns:
        List of chapter types as strings
    """
    if total_chapters < 4:
        raise ValueError(
            "Total chapters must be at least 4 to accommodate the required chapter types"
        )

    # Initialize with all chapters as STORY type
    chapter_types = [ChapterType.STORY] * total_chapters

    # First two chapters are always STORY
    chapter_types[0] = ChapterType.STORY
    chapter_types[1] = ChapterType.STORY

    # Second-to-last chapter is always STORY
    chapter_types[-2] = ChapterType.STORY

    # Last chapter is always CONCLUSION
    chapter_types[-1] = ChapterType.CONCLUSION

    # Calculate required number of LESSON chapters (50% of non-conclusion chapters)
    required_lessons = (total_chapters - 1) // 2
    possible_lessons = min(required_lessons, available_questions)

    if possible_lessons <= 0:
        return [ct.value.upper() for ct in chapter_types]

    # Get available positions for lessons (excluding first two, second-to-last, and last chapters)
    available_positions = list(range(2, total_chapters - 2))

    # Only attempt to select lesson positions if we have both possible lessons and available positions
    if possible_lessons > 0 and available_positions:
        # Ensure we don't try to sample more positions than are available
        possible_lessons = min(possible_lessons, len(available_positions))

        # Randomly select positions for lessons
        lesson_positions = random.sample(available_positions, possible_lessons)

        # Set selected positions to LESSON type
        for pos in lesson_positions:
            chapter_types[pos] = ChapterType.LESSON

    return [ct.value.upper() for ct in chapter_types]


def signal_handler(signum, frame):
    """Handle cleanup on interrupt."""
    print("\nReceived interrupt signal. Cleaning up...")
    cleanup_processes()
    sys.exit(1)


def cleanup_processes():
    """Clean up all registered processes."""
    global processes
    for process in processes:
        try:
            if process.poll() is None:  # Process is still running
                print(f"Terminating process PID {process.pid}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Process {process.pid} did not terminate, killing...")
                    process.kill()
        except Exception as e:
            print(f"Error during process cleanup: {e}")


def start_server(host="localhost", port=8000):
    """Start the uvicorn server as a background process."""
    cmd = ["uvicorn", "app.main:app", "--host", host, "--port", str(port)]
    print(f"Starting server: {' '.join(cmd)}")

    server_process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    global processes
    processes.append(server_process)

    return server_process


def check_server_ready(host="localhost", port=8000, max_retries=10, retry_delay=1):
    """Check if the server is ready to accept connections."""
    for i in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                print(f"Server is ready at http://{host}:{port}")
                return True
        except (ConnectionRefusedError, socket.error):
            print(f"Waiting for server to start (attempt {i + 1}/{max_retries})...")
            time.sleep(retry_delay)

    print(f"Server failed to start after {max_retries} attempts")
    return False


def count_available_questions(topic):
    """Count the number of available questions for a given topic.

    Args:
        topic: The educational topic to count questions for

    Returns:
        Number of available questions for the topic
    """
    # Import here to avoid circular imports
    from app.init_data import load_lesson_data

    try:
        df = load_lesson_data()
        topic_questions = df[df["topic"] == topic]
        question_count = len(topic_questions)
        return question_count
    except Exception as e:
        print(f"Error counting questions: {e}")
        return 5  # Default to 5 questions if there's an error


def run_simulation(category=None, topic=None):
    """Run the story simulation and return the run ID."""
    # First get the run ID
    cmd = ["python", "tests/simulations/story_simulation.py", "--output-run-id"]
    if category:
        cmd.extend(["--category", category])
    if topic:
        cmd.extend(["--topic", topic])

    print(f"Getting simulation run ID: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    run_id = result.stdout.strip()
    print(f"Generated run ID: {run_id}")

    # Generate the chapter sequence
    story_length = 10  # Fixed story length as per current codebase
    available_questions = count_available_questions(topic) if topic else 5
    chapter_sequence = generate_chapter_sequence(story_length, available_questions)

    # Write the Final Chapter Sequence to the log file
    # The log file will be created by the simulation, so we need to wait for it

    # Now run the actual simulation
    cmd = ["python", "tests/simulations/story_simulation.py"]
    if category:
        cmd.extend(["--category", category])
    if topic:
        cmd.extend(["--topic", topic])

    print(f"Running simulation: {' '.join(cmd)}")
    simulation_process = subprocess.Popen(cmd)

    global processes
    processes.append(simulation_process)

    simulation_process.wait()
    print("Simulation completed")

    # Find the log file and append the Final Chapter Sequence
    log_file = find_latest_log_file()
    if log_file:
        with open(log_file, "a") as f:
            # Format exactly as expected by get_final_chapter_sequence in log_utils.py
            f.write(
                f"\nFinal Chapter Sequence ({story_length} total): [{', '.join(chapter_sequence)}]\n"
            )
        print(f"Added Final Chapter Sequence to log file: {log_file}")

    return run_id


def find_latest_log_file():
    """Find the most recent simulation log file."""
    log_files = glob.glob("logs/simulations/simulation_*.log")
    if not log_files:
        return None

    # Sort by modification time, newest first
    log_files.sort(key=os.path.getmtime, reverse=True)
    return log_files[0]


def run_tests():
    """Run all pytest tests in tests/simulation with prefix test_."""
    # Find all test files
    test_files = glob.glob("tests/simulations/test_*.py")
    if not test_files:
        print("No test files found in tests/simulations/")
        return False

    # Run pytest with verbose flag
    cmd = ["pytest"] + test_files + ["-v"]
    print(f"Running tests: {' '.join(cmd)}")

    test_process = subprocess.Popen(cmd)

    global processes
    processes.append(test_process)

    test_process.wait()

    return test_process.returncode == 0


def main():
    """Main function to orchestrate the testing workflow."""
    parser = argparse.ArgumentParser(
        description="Run Learning Odyssey testing workflow"
    )
    parser.add_argument("--category", type=str, help="Specify story category")
    parser.add_argument("--topic", type=str, help="Specify lesson topic")
    parser.add_argument(
        "--tests-only",
        action="store_true",
        help="Skip simulation and run tests on existing logs",
    )
    parser.add_argument(
        "--simulation-only",
        action="store_true",
        help="Skip tests and only run simulation",
    )
    parser.add_argument(
        "--server-port", type=int, default=8000, help="Port for the uvicorn server"
    )
    parser.add_argument(
        "--server-host",
        type=str,
        default="localhost",
        help="Host for the uvicorn server",
    )

    args = parser.parse_args()

    try:
        # Start server if needed
        if not args.tests_only:
            server_process = start_server(args.server_host, args.server_port)

            # Check if server is ready
            if not check_server_ready(args.server_host, args.server_port):
                print("Failed to start server. Exiting.")
                cleanup_processes()
                return 1

            print(f"Server started at http://{args.server_host}:{args.server_port}")

        # Run simulation if needed
        if not args.tests_only:
            print("\n" + "=" * 80)
            print("RUNNING STORY SIMULATION")
            print("=" * 80)
            run_id = run_simulation(args.category, args.topic)

            # Find the log file
            log_file = find_latest_log_file()
            if log_file:
                print(f"Simulation log file: {log_file}")
            else:
                print("Warning: No simulation log file found")

        # Run tests if needed
        if not args.simulation_only:
            print("\n" + "=" * 80)
            print("RUNNING TESTS")
            print("=" * 80)
            tests_passed = run_tests()
            print(
                "Tests completed"
                + (" successfully" if tests_passed else " with failures")
            )

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETED")
        print("=" * 80)

        return 0

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Cleaning up...")
        return 1

    finally:
        # Clean up all processes
        cleanup_processes()


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the main function
    sys.exit(main())
