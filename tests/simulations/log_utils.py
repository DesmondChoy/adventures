"""
Utility functions for working with simulation log files.

This module provides helper functions for finding, parsing, and analyzing
simulation log files generated by story_simulation.py.

These utilities are designed to be used by test scripts to:
1. Find specific simulation runs by ID, date, or criteria
2. Parse log files to extract structured data
3. Analyze simulation results for test assertions
"""

import os
import glob
import json
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def get_latest_simulation_log() -> str:
    """Get the path to the most recent simulation log file.

    Returns:
        str: Path to the most recent simulation log file
    """
    log_files = glob.glob("logs/simulations/simulation_*.log")
    if not log_files:
        raise FileNotFoundError("No simulation log files found")
    return max(log_files, key=os.path.getctime)


def get_simulation_logs_by_date(date_str: str) -> List[str]:
    """Get paths to simulation logs from a specific date.

    Args:
        date_str (str): Date string in YYYY-MM-DD format

    Returns:
        List[str]: List of paths to matching log files
    """
    pattern = f"logs/simulations/simulation_{date_str}_*.log"
    return glob.glob(pattern)


def get_simulation_log_by_run_id(run_id: str) -> Optional[str]:
    """Find a simulation log by its run ID.

    Args:
        run_id (str): The run ID to search for

    Returns:
        Optional[str]: Path to the matching log file, or None if not found
    """
    pattern = f"logs/simulations/simulation_*_{run_id}.log"
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def find_simulations_by_criteria(
    story_category: Optional[str] = None,
    lesson_topic: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
) -> List[str]:
    """Find simulation runs matching specific criteria.

    Args:
        story_category (Optional[str]): Filter by story category
        lesson_topic (Optional[str]): Filter by lesson topic
        min_date (Optional[str]): Minimum date in YYYY-MM-DD format
        max_date (Optional[str]): Maximum date in YYYY-MM-DD format

    Returns:
        List[str]: List of paths to matching log files
    """
    matching_runs = []

    # Convert date strings to datetime objects if provided
    min_datetime = datetime.fromisoformat(f"{min_date}T00:00:00") if min_date else None
    max_datetime = datetime.fromisoformat(f"{max_date}T23:59:59") if max_date else None

    for log_file in glob.glob("logs/simulations/simulation_*.log"):
        # Extract date from filename for date filtering
        filename = os.path.basename(log_file)
        match = re.match(
            r"simulation_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_.*\.log", filename
        )

        if match:
            file_date_str = match.group(1)
            file_time_str = match.group(2).replace("-", ":")
            file_datetime = datetime.fromisoformat(f"{file_date_str}T{file_time_str}")

            # Apply date filters if specified
            if min_datetime and file_datetime < min_datetime:
                continue
            if max_datetime and file_datetime > max_datetime:
                continue

        # Check content criteria if specified
        if story_category is not None or lesson_topic is not None:
            with open(log_file, "r") as f:
                for line in f:
                    if "SIMULATION_RUN_START" in line:
                        try:
                            # Extract the JSON part of the log entry
                            json_str = line.split(" - ")[2]
                            data = json.loads(json_str)

                            # Check if criteria match
                            category_match = (
                                story_category is None
                                or data.get("story_category") == story_category
                            )
                            topic_match = (
                                lesson_topic is None
                                or data.get("lesson_topic") == lesson_topic
                            )

                            if category_match and topic_match:
                                matching_runs.append(log_file)
                        except (IndexError, json.JSONDecodeError):
                            # Skip malformed log entries
                            pass
                        break
        else:
            # If no content criteria specified, include all files that passed date filter
            matching_runs.append(log_file)

    return matching_runs


def parse_simulation_log(log_file: str) -> Dict[str, Any]:
    """Parse a simulation log file into structured data.

    Args:
        log_file (str): Path to the log file

    Returns:
        Dict[str, Any]: Structured data extracted from the log
    """
    result = {
        "run_id": None,
        "timestamp": None,
        "story_category": None,
        "lesson_topic": None,
        "story_length": None,
        "duration_seconds": None,
        "chapter_types": [],
        "choices": [],
        "lessons": [],
        "stats": {},
        "errors": [],
        "complete": False,
        "events": [],
        "process_executions": [],
        "state_transitions": [],
    }

    with open(log_file, "r") as f:
        for line in f:
            try:
                # Skip non-JSON lines and header lines
                if " - " not in line or line.startswith("==="):
                    continue

                # Extract timestamp, level, and message
                parts = line.split(" - ", 2)
                if len(parts) < 3:
                    continue

                timestamp, level, message = parts

                # Try to parse the message as JSON
                try:
                    # Check if the message is a JSON object
                    if message.strip().startswith("{"):
                        data = json.loads(message)

                        # Store all events for detailed analysis
                        if "message" in data and data["message"].startswith("EVENT:"):
                            event_type = data["message"].split(":", 1)[1]
                            event_data = {
                                "type": event_type,
                                "timestamp": timestamp,
                                "data": {
                                    k: v for k, v in data.items() if k != "message"
                                },
                            }
                            result["events"].append(event_data)

                            # Process specific event types
                            if event_type == "CHAPTER_START":
                                result["chapter_types"].append(
                                    {
                                        "chapter_number": data.get("chapter_number"),
                                        "type": data.get("chapter_type", "").upper(),
                                        "chapter_id": data.get("chapter_id"),
                                    }
                                )

                            elif event_type == "CHOICE_SELECTED":
                                result["choices"].append(
                                    {
                                        "text": data.get("choice_text"),
                                        "id": data.get("choice_id"),
                                        "chapter_number": data.get("chapter_number"),
                                    }
                                )

                            elif event_type == "LESSON_ANSWER":
                                result["lessons"].append(
                                    {
                                        "is_correct": data.get("is_correct"),
                                        "selected": data.get("selected_answer"),
                                        "correct": data.get("correct_answer"),
                                        "chapter_number": data.get("chapter_number"),
                                    }
                                )

                            elif event_type == "PROCESS_START":
                                result["process_executions"].append(
                                    {
                                        "process_name": data.get("process_name"),
                                        "chapter_number": data.get("chapter_number"),
                                        "chapter_type": data.get("chapter_type"),
                                        "timestamp": data.get("timestamp"),
                                    }
                                )

                            elif event_type == "STATE_TRANSITION":
                                result["state_transitions"].append(
                                    {
                                        "from_chapter": data.get("from_chapter"),
                                        "to_chapter": data.get("to_chapter"),
                                        "timestamp": data.get("timestamp"),
                                    }
                                )

                            elif event_type == "STORY_COMPLETE":
                                result["stats"] = {
                                    "total_lessons": data.get("total_lessons", 0),
                                    "correct_answers": data.get("correct_answers", 0),
                                    "success_rate": data.get("success_rate", 0),
                                }
                                result["complete"] = True

                        # Handle legacy format for backward compatibility
                        elif "SIMULATION_RUN_START" in message:
                            result["run_id"] = data.get("run_id")
                            result["timestamp"] = data.get("timestamp")
                            result["story_category"] = data.get("story_category")
                            result["lesson_topic"] = data.get("lesson_topic")
                            result["story_length"] = data.get("story_length")

                        elif "SIMULATION_RUN_END" in message:
                            result["duration_seconds"] = data.get("duration_seconds")
                            result["complete"] = True
                except json.JSONDecodeError:
                    # Handle non-JSON messages using regex patterns for backward compatibility

                    # Process chapter types (legacy format)
                    if "CHAPTER_TYPE:" in message:
                        match = re.search(
                            r"CHAPTER_TYPE: (\w+) \(Chapter (\d+)\)", message
                        )
                        if match:
                            chapter_type = match.group(1)
                            chapter_num = int(match.group(2))
                            # Only add if not already present
                            if not any(
                                c["chapter_number"] == chapter_num
                                for c in result["chapter_types"]
                            ):
                                result["chapter_types"].append(
                                    {
                                        "chapter_number": chapter_num,
                                        "type": chapter_type,
                                    }
                                )

                    # Process choices (legacy format)
                    elif "CHOICE:" in message:
                        match = re.search(
                            r"CHOICE: Selected '([^']+)' \(ID: ([^)]+)\)", message
                        )
                        if match:
                            choice_text = match.group(1)
                            choice_id = match.group(2)
                            result["choices"].append(
                                {"text": choice_text, "id": choice_id}
                            )

                    # Process lesson answers (legacy format)
                    elif "LESSON:" in message:
                        match = re.search(
                            r"LESSON: Answer is (CORRECT|INCORRECT) - Selected: '([^']+)', Correct: '([^']+)'",
                            message,
                        )
                        if match:
                            is_correct = match.group(1) == "CORRECT"
                            selected = match.group(2)
                            correct = match.group(3)
                            result["lessons"].append(
                                {
                                    "is_correct": is_correct,
                                    "selected": selected,
                                    "correct": correct,
                                }
                            )

                    # Process stats (legacy format)
                    elif "STATS:" in message:
                        if "Total Lessons:" in message:
                            match = re.search(r"STATS: Total Lessons: (\d+)", message)
                            if match:
                                result["stats"]["total_lessons"] = int(match.group(1))
                        elif "Correct Answers:" in message:
                            match = re.search(r"STATS: Correct Answers: (\d+)", message)
                            if match:
                                result["stats"]["correct_answers"] = int(match.group(1))
                        elif "Success Rate:" in message:
                            match = re.search(r"STATS: Success Rate: (\d+)%", message)
                            if match:
                                result["stats"]["success_rate"] = int(match.group(1))

                # Process errors
                if level == "ERROR":
                    result["errors"].append(
                        {"timestamp": timestamp, "message": message.strip()}
                    )

            except Exception as e:
                # Skip problematic lines
                continue

    return result


def get_chapter_sequence(log_file: str) -> List[str]:
    """Extract the sequence of chapter types from a simulation log.

    Args:
        log_file (str): Path to the log file

    Returns:
        List[str]: Sequence of chapter types in order
    """
    parsed_data = parse_simulation_log(log_file)
    # Sort by chapter number and extract types
    sorted_chapters = sorted(
        parsed_data["chapter_types"], key=lambda x: x["chapter_number"]
    )
    return [chapter["type"] for chapter in sorted_chapters]


def count_lesson_chapters(log_file: str) -> int:
    """Count the number of lesson chapters in a simulation.

    Args:
        log_file (str): Path to the log file

    Returns:
        int: Number of lesson chapters
    """
    chapter_types = get_chapter_sequence(log_file)
    return chapter_types.count("LESSON")


def get_lesson_success_rate(log_file: str) -> float:
    """Calculate the success rate for lesson questions.

    Args:
        log_file (str): Path to the log file

    Returns:
        float: Success rate as a percentage (0-100)
    """
    parsed_data = parse_simulation_log(log_file)
    lessons = parsed_data["lessons"]

    if not lessons:
        return 0.0

    correct_count = sum(1 for lesson in lessons if lesson["is_correct"])
    return (correct_count / len(lessons)) * 100


def check_simulation_complete(log_file: str) -> bool:
    """Check if a simulation completed successfully.

    Args:
        log_file (str): Path to the log file

    Returns:
        bool: True if the simulation completed successfully
    """
    parsed_data = parse_simulation_log(log_file)
    return parsed_data["complete"] and not parsed_data["errors"]


def get_simulation_errors(log_file: str) -> List[Dict[str, str]]:
    """Get all errors from a simulation run.

    Args:
        log_file (str): Path to the log file

    Returns:
        List[Dict[str, str]]: List of error objects with timestamp and message
    """
    parsed_data = parse_simulation_log(log_file)
    return parsed_data["errors"]


def get_process_executions(
    log_file: str, process_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all process executions from a simulation run.

    Args:
        log_file (str): Path to the log file
        process_name (Optional[str]): Filter by process name

    Returns:
        List[Dict[str, Any]]: List of process execution objects
    """
    parsed_data = parse_simulation_log(log_file)
    if process_name:
        return [
            p
            for p in parsed_data["process_executions"]
            if p["process_name"] == process_name
        ]
    return parsed_data["process_executions"]


def check_process_after_chapter_type(
    log_file: str, process_name: str, chapter_type: str
) -> bool:
    """Check if a process is executed after chapters of a specific type.

    Args:
        log_file (str): Path to the log file
        process_name (str): The process name to check for
        chapter_type (str): The chapter type to check after

    Returns:
        bool: True if the process is executed after the specified chapter type
    """
    parsed_data = parse_simulation_log(log_file)

    # Get all chapter numbers of the specified type
    chapter_numbers = [
        c["chapter_number"]
        for c in parsed_data["chapter_types"]
        if c["type"].upper() == chapter_type.upper()
    ]

    # Check if the process is executed for any of these chapter numbers
    for process in parsed_data["process_executions"]:
        if (
            process["process_name"] == process_name
            and process["chapter_number"] in chapter_numbers
        ):
            return True

    return False


def get_llm_interactions(log_file: str) -> List[Dict[str, Any]]:
    """Extract LLM prompts and responses from a simulation log.

    Args:
        log_file (str): Path to the log file

    Returns:
        List[Dict[str, Any]]: List of LLM interaction objects
    """
    # This is a placeholder for future implementation
    # Currently, the simulation doesn't log LLM prompts and responses directly
    # This function will be implemented when LLM logging is added
    return []


def get_state_transitions(log_file: str) -> List[Dict[str, Any]]:
    """Get all state transitions from a simulation run.

    Args:
        log_file (str): Path to the log file

    Returns:
        List[Dict[str, Any]]: List of state transition objects
    """
    parsed_data = parse_simulation_log(log_file)
    return parsed_data["state_transitions"]


def verify_chapter_sequence_pattern(log_file: str, pattern: List[str]) -> bool:
    """Check if the chapter sequence follows a specific pattern.

    Args:
        log_file (str): Path to the log file
        pattern (List[str]): The pattern to check for (e.g., ["STORY", "LESSON", "STORY"])

    Returns:
        bool: True if the pattern is found in the chapter sequence
    """
    chapter_sequence = get_chapter_sequence(log_file)

    # Convert all types to uppercase for case-insensitive comparison
    chapter_sequence = [c.upper() for c in chapter_sequence]
    pattern = [p.upper() for p in pattern]

    # Check if the pattern appears in the sequence
    for i in range(len(chapter_sequence) - len(pattern) + 1):
        if chapter_sequence[i : i + len(pattern)] == pattern:
            return True

    return False


if __name__ == "__main__":
    # Example usage
    try:
        latest_log = get_latest_simulation_log()
        print(f"Latest simulation log: {latest_log}")

        parsed_data = parse_simulation_log(latest_log)
        print(f"Run ID: {parsed_data['run_id']}")
        print(f"Story Category: {parsed_data['story_category']}")
        print(f"Lesson Topic: {parsed_data['lesson_topic']}")

        # Basic log analysis
        print("\n=== Basic Log Analysis ===")
        chapter_sequence = get_chapter_sequence(latest_log)
        print(f"Chapter Sequence: {chapter_sequence}")

        lesson_count = count_lesson_chapters(latest_log)
        print(f"Lesson Chapters: {lesson_count}")

        success_rate = get_lesson_success_rate(latest_log)
        print(f"Lesson Success Rate: {success_rate:.1f}%")

        is_complete = check_simulation_complete(latest_log)
        print(f"Simulation Complete: {is_complete}")

        # Process execution analysis
        print("\n=== Process Execution Analysis ===")
        process_executions = get_process_executions(latest_log)
        print(f"Total Process Executions: {len(process_executions)}")

        # Count by process name
        process_counts = {}
        for process in process_executions:
            process_name = process["process_name"]
            process_counts[process_name] = process_counts.get(process_name, 0) + 1

        for process_name, count in process_counts.items():
            print(f"  {process_name}: {count} executions")

        # Check specific process patterns
        has_consequences_after_lesson = check_process_after_chapter_type(
            latest_log, "process_consequences", "LESSON"
        )
        print(f"Consequences after Lesson: {has_consequences_after_lesson}")

        # State transition analysis
        print("\n=== State Transition Analysis ===")
        state_transitions = get_state_transitions(latest_log)
        print(f"Total State Transitions: {len(state_transitions)}")

        # Chapter sequence pattern verification
        print("\n=== Chapter Sequence Pattern Analysis ===")
        story_lesson_story = verify_chapter_sequence_pattern(
            latest_log, ["STORY", "LESSON", "STORY"]
        )
        print(f"Story-Lesson-Story Pattern: {story_lesson_story}")

        lesson_lesson = verify_chapter_sequence_pattern(
            latest_log, ["LESSON", "LESSON"]
        )
        print(f"Consecutive Lessons Pattern: {lesson_lesson}")

        # Error analysis
        print("\n=== Error Analysis ===")
        errors = get_simulation_errors(latest_log)
        if errors:
            print(f"Errors: {len(errors)}")
            for error in errors:
                print(f"  {error['timestamp']}: {error['message']}")
        else:
            print("No errors")

    except FileNotFoundError:
        print("No simulation logs found")
