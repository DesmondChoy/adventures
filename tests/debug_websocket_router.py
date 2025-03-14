import sys
import os
import json
import asyncio
import logging
from pprint import pformat

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.websocket_service import process_summary_request
from app.services.adventure_state_manager import AdventureStateManager
from app.models.story import AdventureState, ChapterType, ChapterData

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("debug_router")


class MockWebSocket:
    """Mock WebSocket class to test router handling."""

    def __init__(self):
        self.sent_messages = []
        self.sent_json = []
        self.sent_text = []

    async def send_json(self, data):
        logger.info(f"WebSocket sent JSON: {json.dumps(data, indent=2)[:100]}...")
        self.sent_json.append(data)
        self.sent_messages.append(data)

    async def send_text(self, text):
        logger.info(f"WebSocket sent text: {text[:100]}...")
        self.sent_text.append(text)
        self.sent_messages.append(text)

    async def receive_json(self):
        # Mock method to simulate receiving JSON
        return {"type": "request_summary", "state": self.test_state}


async def test_direct_summary_handling():
    """Test the summary request handling directly."""
    mock_socket = MockWebSocket()
    state_manager = AdventureStateManager()

    # Create a minimal state for testing
    state = AdventureState(
        current_chapter_id="conclusion",
        story_length=10,
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

    # Store the state in the state manager
    state_manager.state = state

    # Also store in the mock socket for the receive_json mock
    mock_socket.test_state = state.dict()

    logger.info("Testing direct summary request handling")

    try:
        # Process the summary request directly
        await process_summary_request(state_manager, mock_socket)

        logger.info("Summary request processed without errors")
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

        return mock_socket.sent_messages
    except Exception as e:
        logger.error(f"Error in summary handling: {e}", exc_info=True)
        return None


async def main():
    response_messages = await test_direct_summary_handling()
    logger.info("Test completed")


if __name__ == "__main__":
    asyncio.run(main())
