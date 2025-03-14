import sys
import os
import json
import asyncio
import logging
from pprint import pformat

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.story import AdventureState, ChapterType, ChapterData
from app.services.websocket_service import (
    process_summary_request,
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
            return {"type": "request_summary", "state": self.test_state}
        else:
            return {"type": "request_summary", "state": {}}


def extract_chapter_summaries_from_log(log_file):
    """Extract chapter summaries from the simulation log."""
    summaries = []
    all_summaries_found = False
    lesson_questions = []  # Store lesson questions

    with open(log_file, "r") as f:
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
            if "EVENT:ALL_CHAPTER_SUMMARIES" in line:
                try:
                    data = json.loads(line)
                    if "extra" in data and "chapter_summaries" in data["extra"]:
                        all_summaries = data["extra"]["chapter_summaries"]
                        if all_summaries and len(all_summaries) > 0:
                            # If we found comprehensive summaries, use those instead
                            summaries = all_summaries
                            all_summaries_found = True
                            break  # No need to continue parsing
                except json.JSONDecodeError:
                    pass

            # Look for lesson questions
            if "EVENT:LESSON_QUESTION" in line:
                try:
                    data = json.loads(line)
                    if "question" in data:
                        question = data.get("question", "")
                        topic = data.get("topic", "")
                        subtopic = data.get("subtopic", "")
                        correct_answer = data.get("correct_answer", "")

                        if question and correct_answer:
                            lesson_questions.append(
                                {
                                    "question": question,
                                    "topic": topic,
                                    "subtopic": subtopic,
                                    "correct_answer": correct_answer,
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
                                summaries = chapter_summaries

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
                                summaries = chapter_summaries
                                all_summaries_found = (
                                    True  # These are the most complete summaries
                                )
                except Exception as e:
                    logging.getLogger("debug_summary").error(
                        f"Error parsing STORY_COMPLETE: {e}"
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


async def test_process_summary_request(state):
    """Test the process_summary_request function with a mock websocket."""
    logger.info("Testing process_summary_request function")

    mock_socket = MockWebSocket()
    state_manager = AdventureStateManager()

    # Set the test state in the mock socket
    mock_socket.test_state = state.model_dump()

    # Set the state in the state manager
    state_manager.state = state

    try:
        await process_summary_request(state_manager, mock_socket)
        logger.info("process_summary_request completed without errors")

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

        return mock_socket.sent_json, mock_socket.sent_text
    except Exception as e:
        logger.error(f"Error in process_summary_request: {e}", exc_info=True)
        return None, None


async def main():
    # Path to your simulation log
    log_file = "logs/simulations/simulation_2025-03-11_23-36-15_8e1a3e7c.log"

    # Extract chapter summaries
    logger.info(f"Extracting chapter summaries from {log_file}")
    summaries, lesson_questions = extract_chapter_summaries_from_log(log_file)
    logger.info(f"Found {len(summaries)} chapter summaries")
    logger.info(f"Found {len(lesson_questions)} lesson questions")

    # Create test state
    state = await create_test_state(summaries)
    logger.info(f"Created test state with {len(state.chapters)} chapters")

    # Test generate_summary_content
    summary_content = await test_generate_summary_content(state)

    # Test process_summary_request
    json_messages, text_messages = await test_process_summary_request(state)

    logger.info("Tests completed")


if __name__ == "__main__":
    asyncio.run(main())
