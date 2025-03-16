import sys
import os
import json
import asyncio
import logging
import glob
import re
from pprint import pformat
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.story import AdventureState, ChapterType, ChapterData
from app.services.websocket_service import (
    generate_summary_content,
)
from app.services.adventure_state_manager import AdventureStateManager
from app.services.chapter_manager import ChapterManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("debug_summary")


class MockWebSocket:
    """Mock WebSocket class to capture messages."""

    def __init__(self):
        self.sent_messages = []
        self.sent_json = []
        self.sent_text = []
        self.test_state = None

    async def send_json(self, data):
        logger.info(f"WebSocket sent JSON: {json.dumps(data, indent=2)}")
        self.sent_json.append(data)

    async def send_text(self, text):
        if len(text) < 100:
            logger.debug(f"WebSocket sent text: {text}")
        else:
            logger.debug(f"WebSocket sent text (truncated): {text[:100]}...")
        self.sent_text.append(text)

    async def receive_json(self):
        """Mock method to simulate receiving JSON data."""
        if self.test_state:
            return {"type": "choice", "id": "reveal_summary", "state": self.test_state}
        else:
            return {"type": "choice", "id": "reveal_summary", "state": {}}


def extract_chapter_summaries_from_log(log_file):
    """Extract chapter summaries from the simulation log."""
    summaries = []
    all_summaries_found = False
    lesson_questions = []  # Store lesson questions
    lesson_answers = {}  # Store lesson answers by chapter number

    with open(log_file, "r") as f:
        # First pass: collect lesson answers
        for line in f:
            # Look for lesson answers
            if "EVENT:LESSON_ANSWER" in line:
                try:
                    data = json.loads(line)
                    # The data might be directly in the JSON object or in the "extra" field
                    if "chapter_number" in data:
                        chapter_number = data.get("chapter_number")
                        if chapter_number:
                            lesson_answers[chapter_number] = {
                                "chosen_answer": data.get("selected_answer", ""),
                                "is_correct": data.get("is_correct", False),
                            }
                    elif "extra" in data:
                        extra = data["extra"]
                        chapter_number = extra.get("chapter_number")
                        if chapter_number:
                            lesson_answers[chapter_number] = {
                                "chosen_answer": extra.get("selected_answer", ""),
                                "is_correct": extra.get("is_correct", False),
                            }
                except Exception as e:
                    logger = logging.getLogger("debug_summary")
                    logger.error(f"Error parsing LESSON_ANSWER: {e}")
                    pass

        # Reset file pointer to beginning
        f.seek(0)

        # Second pass: process everything else
        for line in f:
            # First try to find individual chapter summaries
            if "EVENT:CHAPTER_SUMMARY" in line:
                try:
                    # Parse the JSON structure
                    data = json.loads(line)
                    # The summary is in the 'extra' parameters
                    if "extra" in data and "summary" in data["extra"]:
                        summary = data["extra"]["summary"]
                        summaries.append(summary)
                    # Try alternative format where summary might be directly in the data
                    elif "summary" in data:
                        summary = data["summary"]
                        summaries.append(summary)
                except json.JSONDecodeError:
                    # If it's not valid JSON, try to extract using string parsing
                    try:
                        # Look for "summary": "text" pattern
                        import re

                        summary_match = re.search(r'"summary":\s*"([^"]+)"', line)
                        if summary_match:
                            summaries.append(summary_match.group(1))
                    except Exception:
                        pass

            # Also look for the comprehensive summary at the end
            if (
                "EVENT:ALL_CHAPTER_SUMMARIES" in line
                or "EVENT:FINAL_CHAPTER_SUMMARIES" in line
            ):
                try:
                    data = json.loads(line)
                    if "extra" in data and "chapter_summaries" in data["extra"]:
                        all_summaries = data["extra"]["chapter_summaries"]
                        if all_summaries and len(all_summaries) > 0:
                            # If we found comprehensive summaries, use those instead
                            # Prepend chapter numbers to each summary
                            numbered_summaries = []
                            for i, summary in enumerate(all_summaries, 1):
                                numbered_summaries.append(f"Chapter {i}: {summary}")

                            summaries = numbered_summaries
                            all_summaries_found = True
                            logger.info(
                                f"Found {len(all_summaries)} chapter summaries in ALL_CHAPTER_SUMMARIES/FINAL_CHAPTER_SUMMARIES event"
                            )
                            break  # No need to continue parsing
                except json.JSONDecodeError:
                    pass

            # Look for lesson questions
            if "EVENT:LESSON_QUESTION" in line:
                try:
                    data = json.loads(line)
                    chapter_number = None

                    # Extract chapter number from the data
                    if "chapter_number" in data:
                        # Data is directly in the JSON object
                        chapter_number = data.get("chapter_number")
                        question = data.get("question", "")
                        topic = data.get("topic", "")
                        subtopic = data.get("subtopic", "")
                        correct_answer = data.get("correct_answer", "")
                        explanation = data.get("explanation", "")
                    elif "extra" in data:
                        # Data is in the "extra" field
                        extra = data["extra"]
                        chapter_number = extra.get("chapter_number")
                        question = extra.get("question", "")
                        topic = extra.get("topic", "")
                        subtopic = extra.get("subtopic", "")
                        correct_answer = extra.get("correct_answer", "")
                        explanation = extra.get("explanation", "")
                    else:
                        # Fallback to looking for fields directly in the data
                        question = data.get("question", "")
                        topic = data.get("topic", "")
                        subtopic = data.get("subtopic", "")
                        correct_answer = data.get("correct_answer", "")
                        explanation = data.get("explanation", "")

                    # Get chosen answer and correctness from lesson_answers if available
                    chosen_answer = ""
                    is_correct = False
                    if chapter_number and chapter_number in lesson_answers:
                        answer_data = lesson_answers[chapter_number]
                        chosen_answer = answer_data.get("chosen_answer", "")
                        is_correct = answer_data.get("is_correct", False)

                    if question and correct_answer:
                        lesson_questions.append(
                            {
                                "question": question,
                                "topic": topic,
                                "subtopic": subtopic,
                                "correct_answer": correct_answer,
                                "chosen_answer": chosen_answer,
                                "is_correct": is_correct,
                                "explanation": explanation,
                            }
                        )
                except Exception as e:
                    logger = logging.getLogger("debug_summary")
                    logger.error(f"Error parsing LESSON_QUESTION: {e}")
                    pass

            # Also try to extract from STATE_TRANSITION events which contain chapter content
            if not all_summaries_found and "EVENT:STATE_TRANSITION" in line:
                try:
                    data = json.loads(line)
                    if "state" in data:
                        # The state is a JSON string that needs to be parsed again
                        state_str = data["state"]
                        state_data = json.loads(state_str)

                        # Check if this state contains chapter_summaries
                        if (
                            "chapter_summaries" in state_data
                            and state_data["chapter_summaries"]
                        ):
                            chapter_summaries = state_data["chapter_summaries"]
                            if len(chapter_summaries) > len(summaries):
                                # Prepend chapter numbers to each summary
                                numbered_summaries = []
                                for i, summary in enumerate(chapter_summaries, 1):
                                    numbered_summaries.append(f"Chapter {i}: {summary}")

                                summaries = numbered_summaries
                                logger.info(
                                    f"Found {len(chapter_summaries)} chapter summaries in STATE_TRANSITION event"
                                )

                        # We no longer extract chapter content as fallback summaries
                except Exception as e:
                    logger = logging.getLogger("debug_summary")
                    logger.error(f"Error parsing STATE_TRANSITION: {e}")
                    pass

            # Extract chapter summaries from STORY_COMPLETE event
            if not all_summaries_found and "EVENT:STORY_COMPLETE" in line:
                try:
                    data = json.loads(line)
                    if "final_state" in data:
                        # The final_state is a JSON string that needs to be parsed again
                        final_state_str = data["final_state"]
                        final_state_data = json.loads(final_state_str)

                        # Check if this final state contains chapter_summaries
                        if (
                            "chapter_summaries" in final_state_data
                            and final_state_data["chapter_summaries"]
                        ):
                            chapter_summaries = final_state_data["chapter_summaries"]
                            if len(chapter_summaries) > len(summaries):
                                logging.getLogger("debug_summary").info(
                                    f"Found {len(chapter_summaries)} chapter summaries in STORY_COMPLETE event"
                                )
                                # Prepend chapter numbers to each summary
                                numbered_summaries = []
                                for i, summary in enumerate(chapter_summaries, 1):
                                    numbered_summaries.append(f"Chapter {i}: {summary}")

                                summaries = numbered_summaries
                                all_summaries_found = (
                                    True  # These are the most complete summaries
                                )
                except Exception as e:
                    logging.getLogger("debug_summary").error(
                        f"Error parsing STORY_COMPLETE: {e}"
                    )
                    pass

            # Extract chapter summaries from SUMMARY_COMPLETE event
            if not all_summaries_found and "EVENT:SUMMARY_COMPLETE" in line:
                try:
                    data = json.loads(line)
                    if "state" in data:
                        # The state is a JSON string that needs to be parsed again
                        state_str = data["state"]
                        state_data = json.loads(state_str)

                        # Check if this state contains chapter_summaries
                        if (
                            "chapter_summaries" in state_data
                            and state_data["chapter_summaries"]
                        ):
                            chapter_summaries = state_data["chapter_summaries"]
                            if len(chapter_summaries) > len(summaries):
                                logging.getLogger("debug_summary").info(
                                    f"Found {len(chapter_summaries)} chapter summaries in SUMMARY_COMPLETE event"
                                )
                                # Prepend chapter numbers to each summary
                                numbered_summaries = []
                                for i, summary in enumerate(chapter_summaries, 1):
                                    numbered_summaries.append(f"Chapter {i}: {summary}")

                                summaries = numbered_summaries
                                all_summaries_found = (
                                    True  # These are the most complete summaries
                                )
                except Exception as e:
                    logging.getLogger("debug_summary").error(
                        f"Error parsing SUMMARY_COMPLETE: {e}"
                    )
                    pass

    # If no summaries were found, raise an exception
    if not summaries:
        raise ValueError(
            "No chapter summaries found in the log file. Cannot proceed without explicit summaries."
        )

    return summaries, lesson_questions


async def create_test_state(chapter_summaries):
    """Create a test state with the extracted chapter summaries."""
    # Create a minimal state for testing
    state = AdventureState(
        current_chapter_id="conclusion",
        story_length=10,
        chapter_summaries=chapter_summaries,
        current_storytelling_phase="Resolution",
        selected_narrative_elements={"settings": "Test Setting"},
        selected_sensory_details={
            "visuals": "Test Visual",
            "sounds": "Test Sound",
            "smells": "Test Smell",
        },
        selected_theme="Test Theme",
        selected_moral_teaching="Test Moral",
        selected_plot_twist="Test Plot Twist",
        metadata={
            "non_random_elements": {
                "name": "Test Adventure",
                "description": "A test adventure for debugging",
            },
            "agency": {
                "type": "choice",
                "name": "Test Agency",
                "description": "A test agency for debugging",
            },
        },
    )

    # Add 10 dummy chapters to meet requirements
    for i in range(1, 11):
        chapter_type = ChapterType.STORY
        choices = []

        # STORY chapters need exactly 3 choices
        if chapter_type == ChapterType.STORY:
            choices = [
                {
                    "text": f"Test choice 1 for chapter {i}",
                    "next_chapter": f"next_{i}_1",
                },
                {
                    "text": f"Test choice 2 for chapter {i}",
                    "next_chapter": f"next_{i}_2",
                },
                {
                    "text": f"Test choice 3 for chapter {i}",
                    "next_chapter": f"next_{i}_3",
                },
            ]

        # Last chapter should be CONCLUSION with no choices
        if i == 10:
            chapter_type = ChapterType.CONCLUSION
            choices = []

        chapter = ChapterData(
            chapter_number=i,
            content=f"Test content for chapter {i}",
            chapter_type=chapter_type,
            chapter_content={
                "content": f"Test content for chapter {i}",
                "choices": choices,
            },
        )
        state.chapters.append(chapter)

    return state


async def test_generate_summary_content(state):
    """Test the generate_summary_content function directly."""
    logger.info("Testing generate_summary_content function")

    try:
        summary_content = await generate_summary_content(state)
        logger.info(
            f"Summary content generated successfully ({len(summary_content)} chars)"
        )
        logger.debug(f"Summary preview: {summary_content[:200]}...")
        return summary_content
    except Exception as e:
        logger.error(f"Error generating summary content: {e}", exc_info=True)
        return None


async def test_process_reveal_summary(state):
    """Test the process_choice function with 'reveal_summary' choice ID."""
    logger.info("Testing process_choice function with 'reveal_summary' choice ID")

    from app.services.websocket_service import process_choice

    mock_socket = MockWebSocket()
    state_manager = AdventureStateManager()

    # Set the test state in the mock socket
    mock_socket.test_state = state.model_dump()

    # Set the state in the state manager
    state_manager.state = state

    try:
        # Create a choice data dictionary with the 'reveal_summary' choice ID
        choice_data = {
            "id": "reveal_summary",
            "text": "Reveal Your Adventure Summary",
            "state": state.model_dump(),
        }

        # Call process_choice with the 'reveal_summary' choice ID
        result = await process_choice(
            state_manager=state_manager,
            choice_data=choice_data,
            story_category="test_category",
            lesson_topic="test_topic",
            websocket=mock_socket,
        )

        logger.info("process_choice with 'reveal_summary' completed without errors")

        # Check what was sent to the websocket
        logger.info(f"Sent {len(mock_socket.sent_json)} JSON messages")
        logger.info(f"Sent {len(mock_socket.sent_text)} text messages")

        # Check for summary_complete message
        summary_complete_messages = [
            m for m in mock_socket.sent_json if m.get("type") == "summary_complete"
        ]
        if summary_complete_messages:
            logger.info("Found summary_complete message")
        else:
            logger.warning("No summary_complete message found")

        return mock_socket.sent_json, mock_socket.sent_text, result
    except Exception as e:
        logger.error(f"Error in test_process_reveal_summary: {e}", exc_info=True)
        return None, None, None


def find_latest_simulation_log():
    """Find the latest timestamp simulation log file.

    Returns:
        str: Path to the latest simulation log file, or None if no logs found.
    """
    # Path to simulation logs directory
    logs_dir = "logs/simulations"

    # Check if the directory exists
    if not os.path.exists(logs_dir):
        logger.warning(f"Simulation logs directory not found: {logs_dir}")
        return None

    # Pattern for simulation log files
    pattern = os.path.join(logs_dir, "simulation_*.log")

    # Find all simulation log files
    log_files = glob.glob(pattern)

    if not log_files:
        logger.warning(f"No simulation log files found in {logs_dir}")
        return None

    # Extract timestamp from filename and sort by timestamp
    timestamp_pattern = re.compile(r"simulation_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_")

    # Create a list of (file_path, timestamp) tuples
    timestamped_files = []
    for file_path in log_files:
        filename = os.path.basename(file_path)
        match = timestamp_pattern.search(filename)
        if match:
            timestamp_str = match.group(1)
            try:
                # Parse timestamp string to datetime object
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                timestamped_files.append((file_path, timestamp))
            except ValueError:
                logger.warning(f"Failed to parse timestamp from filename: {filename}")

    if not timestamped_files:
        logger.warning("No valid timestamped simulation log files found")
        return None

    # Sort by timestamp (newest first)
    timestamped_files.sort(key=lambda x: x[1], reverse=True)

    # Get the latest log file
    latest_log_file = timestamped_files[0][0]
    logger.info(f"Found latest simulation log: {os.path.basename(latest_log_file)}")

    return latest_log_file


async def main():
    # Find the latest simulation log file
    log_file = find_latest_simulation_log()

    if log_file and os.path.exists(log_file):
        # Extract chapter summaries
        logger.info(f"Extracting chapter summaries from {log_file}")
        summaries, lesson_questions = extract_chapter_summaries_from_log(log_file)
        logger.info(f"Found {len(summaries)} chapter summaries")
        logger.info(f"Found {len(lesson_questions)} lesson questions")

        # Create test state
        state = await create_test_state(summaries)
        logger.info(f"Created test state with {len(state.chapters)} chapters")
    else:
        # Log file doesn't exist, create a sample state with dummy summaries
        logger.warning(f"Log file not found: {log_file}")
        logger.info("Creating sample state with dummy summaries")

        # Create dummy summaries with chapter numbers
        dummy_summaries = [
            f"Chapter {i}: This is a sample summary for chapter {i}. It describes the key events and character development that occurred in this chapter."
            for i in range(1, 11)
        ]

        # Create test state with dummy summaries
        state = await create_test_state(dummy_summaries)
        logger.info(
            f"Created test state with {len(state.chapters)} chapters and {len(dummy_summaries)} dummy summaries"
        )

    # Test generate_summary_content
    summary_content = await test_generate_summary_content(state)

    # Test process_choice with 'reveal_summary' choice ID
    json_messages, text_messages, result = await test_process_reveal_summary(state)

    logger.info("Tests completed")


if __name__ == "__main__":
    asyncio.run(main())
