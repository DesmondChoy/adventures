"""
Story simulation for testing WebSocket router and service integration.

This simulation tests both:
1. WebSocket Router (`app/routers/websocket_router.py`):
   - Connection management
   - Message routing
   - State initialization
   - Error handling at transport level

2. WebSocket Service (`app/services/websocket_service.py`):
   - Business logic processing
   - Content generation
   - State management
   - Error handling at application level

The simulation generates random adventures and validates the entire
story generation pipeline, including router-service interaction.

Updates (2025-02-25):
- Fixed file path for story data (new_stories.yaml)
- Updated initial state structure to match AdventureStateManager expectations
- Enhanced response handling for different message types
- Added support for lesson chapter detection and answer validation
- Improved logging for chapter types and question handling
- Fixed story length to match codebase (constant 10 chapters)
- Optimized for automated testing by removing real-time content streaming
- Enhanced logging for better test analysis and debugging
"""

import asyncio
import websockets
import json
import random
import yaml
import pandas as pd
import logging
import urllib.parse
import signal
import time
from enum import Enum


# Custom error types for router vs service errors
class SimulationErrorType(Enum):
    ROUTER = "router"
    SERVICE = "service"
    STATE = "state"
    CONTENT = "content"


class SimulationError(Exception):
    def __init__(self, error_type: SimulationErrorType, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(f"{error_type.value.upper()}: {message}")


# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG - Ensure DEBUG level for simulation
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/simulation_debug.log"),
        logging.StreamHandler(),
    ],
)
# Configure websockets logger to only show warnings and errors
logging.getLogger("websockets").setLevel(logging.WARNING)
# Allow debug logs from story_app logger - CRITICAL FIX: Get the story_app logger
logger = logging.getLogger("story_app")
logger.setLevel(logging.DEBUG)  # Ensure story_app logger is also at DEBUG level

simulation_logger = logging.getLogger(
    __name__
)  # Keep a separate logger for simulation script itself
simulation_logger.setLevel(
    logging.DEBUG
)  # Set simulation script logger to DEBUG as well

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
WEBSOCKET_TIMEOUT = 30  # seconds

# Global variables for cleanup
websocket = None
should_exit = False


def signal_handler(signum, frame):
    """Handle cleanup on interrupt"""
    global should_exit
    simulation_logger.info("\nReceived interrupt signal. Cleaning up...")
    should_exit = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def print_separator(title=""):
    """Print a visual separator with optional title."""
    width = 80
    if title:
        padding = (width - len(title) - 2) // 2
        print("\n" + "=" * padding + f" {title} " + "=" * padding)
    else:
        print("\n" + "=" * width)


def load_story_data():
    """Load story data from YAML file."""
    try:
        with open("app/data/new_stories.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        simulation_logger.error(f"Failed to load story data: {e}")
        return {"story_categories": {}}


def load_lesson_data():
    """Load lesson data from CSV file."""
    try:
        return pd.read_csv("app/data/lessons.csv")
    except Exception as e:
        simulation_logger.error(f"Failed to load lesson data: {e}")
        return pd.DataFrame(columns=["topic"])


def get_random_story_category(story_data):
    """Randomly select a story category."""
    categories = list(story_data["story_categories"].keys())
    return random.choice(categories)


def get_random_lesson_topic(lesson_df):
    """Randomly select a lesson topic."""
    topics = lesson_df["topic"].unique()
    return random.choice(topics)


# Fixed story length as per current codebase
STORY_LENGTH = 10  # Fixed story length in the current codebase


async def simulate_story():
    global websocket, should_exit

    # Load data and make random selections
    story_data = load_story_data()
    lesson_df = load_lesson_data()

    story_category = get_random_story_category(story_data)
    lesson_topic = get_random_lesson_topic(lesson_df)
    story_length = STORY_LENGTH  # Use the fixed story length

    print_separator("Story Configuration")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Category: {story_category}")
    print(f"Topic: {lesson_topic}")
    print(f"Length: {story_length} chapters")
    print(
        f"WebSocket URI: ws://localhost:8000/ws/story/{urllib.parse.quote(story_category)}/{urllib.parse.quote(lesson_topic)}"
    )
    print("=" * 80)

    # Remove duplicate logging of configuration
    simulation_logger.debug(
        f"Starting story simulation with: Category='{story_category}', Topic='{lesson_topic}', Length={story_length} chapters"
    )

    uri = f"ws://localhost:8000/ws/story/{urllib.parse.quote(story_category)}/{urllib.parse.quote(lesson_topic)}"
    simulation_logger.debug("Attempting WebSocket connection...")

    # Add retry logic for WebSocket connection
    for retry in range(MAX_RETRIES):
        if should_exit:
            simulation_logger.info("Received exit signal during retry loop")
            return

        try:
            websocket = await websockets.connect(uri)
            simulation_logger.info("WebSocket connection established.")

            try:
                # Send initial state message with story length
                # Note: The actual state initialization is handled by AdventureStateManager
                # We only need to provide the story_length here
                initial_state_message = {
                    "state": {
                        "current_chapter_id": "start",
                        "story_length": story_length,
                        "chapters": [],
                        # The following fields are not used by the server but included for completeness
                        "selected_narrative_elements": {},
                        "selected_sensory_details": {},
                        "selected_theme": "",
                        "selected_moral_teaching": "",
                        "selected_plot_twist": "",
                        "planned_chapter_types": [],
                        "current_storytelling_phase": "Exposition",
                        "metadata": {},
                    }
                }
                await websocket.send(json.dumps(initial_state_message))
                simulation_logger.debug(
                    f"Sent initial state: {json.dumps(initial_state_message, indent=2)}"
                )

                # Send 'start' choice to begin story
                start_choice_message = {
                    "state": initial_state_message["state"],
                    "choice": {"chosen_path": "start", "choice_text": "Start Story"},
                }
                await websocket.send(json.dumps(start_choice_message))
                simulation_logger.debug(
                    f"Sent start choice: {json.dumps(start_choice_message, indent=2)}"
                )

                # Chapter generation loop
                current_chapter = 1
                while current_chapter <= story_length and not should_exit:
                    simulation_logger.debug(
                        f"Processing chapter {current_chapter} of {story_length}"
                    )
                    print_separator(f"Chapter {current_chapter}")

                    try:
                        # Initialize variables for story content
                        story_content = []
                        choices_data = None
                        response_state = None

                        while not should_exit:
                            try:
                                response_raw = await asyncio.wait_for(
                                    websocket.recv(), timeout=WEBSOCKET_TIMEOUT
                                )

                                try:
                                    # Try to parse as JSON
                                    response_data = json.loads(response_raw)

                                    # Format JSON responses with proper indentation
                                    if isinstance(response_data, dict):
                                        formatted_json = json.dumps(
                                            response_data, indent=2
                                        )
                                        simulation_logger.debug(
                                            f"Parsed JSON response:\n{formatted_json}"
                                        )

                                        # Handle different response types
                                        response_type = response_data.get("type")

                                        if response_type == "chapter_update":
                                            # Store state for later use
                                            response_state = response_data.get(
                                                "state", {}
                                            )

                                            # Log chapter type information if available
                                            if "current_chapter" in response_state:
                                                chapter_info = response_state[
                                                    "current_chapter"
                                                ]
                                                chapter_type = chapter_info.get(
                                                    "chapter_type", "unknown"
                                                )
                                                # Log chapter type for automated testing
                                                simulation_logger.info(
                                                    f"CHAPTER_TYPE: {chapter_type.upper()} (Chapter {current_chapter})"
                                                )

                                                # If this is a lesson chapter, log question info
                                                if chapter_info.get("question"):
                                                    simulation_logger.debug(
                                                        f"Question: {chapter_info['question'].get('question')}"
                                                    )
                                            continue

                                        elif response_type == "choices":
                                            # Store choices and break the inner loop to process them
                                            choices_data = response_data.get(
                                                "choices", []
                                            )
                                            simulation_logger.debug(
                                                f"Received {len(choices_data)} choices"
                                            )
                                            break

                                        elif response_type == "story_complete":
                                            # Handle story completion
                                            stats = response_data.get("state", {}).get(
                                                "stats", {}
                                            )

                                            # Log detailed statistics for automated testing
                                            simulation_logger.info("Story Complete")
                                            simulation_logger.info(
                                                f"STATS: Total Lessons: {stats.get('total_lessons', 0)}"
                                            )
                                            simulation_logger.info(
                                                f"STATS: Correct Answers: {stats.get('correct_lesson_answers', 0)}"
                                            )
                                            simulation_logger.info(
                                                f"STATS: Success Rate: {stats.get('completion_percentage', 0)}%"
                                            )

                                            # Print for human readability
                                            print_separator("Story Complete")
                                            print(
                                                f"Total Lessons: {stats.get('total_lessons', 0)}"
                                            )
                                            print(
                                                f"Correct Answers: {stats.get('correct_lesson_answers', 0)}"
                                            )
                                            print(
                                                f"Success Rate: {stats.get('completion_percentage', 0)}%"
                                            )
                                            return
                                except json.JSONDecodeError:
                                    # Not JSON, must be story content or completion
                                    story_content.append(response_raw)
                                    # Accumulate content without real-time display
                                    simulation_logger.debug(
                                        f"Received content chunk ({len(response_raw)} chars)"
                                    )
                                except Exception as e:
                                    simulation_logger.error(
                                        f"Error parsing response: {e}"
                                    )
                                    simulation_logger.debug(
                                        f"Problematic response:\n{response_raw}"
                                    )
                                    raise

                            except asyncio.TimeoutError:
                                simulation_logger.error(
                                    f"Timeout waiting for response in chapter {current_chapter}"
                                )
                                raise
                            except websockets.exceptions.ConnectionClosed as e:
                                simulation_logger.error(
                                    f"WebSocket connection closed during chapter {current_chapter}: {e}"
                                )
                                raise

                        if should_exit:
                            break

                        # Log accumulated story content
                        if story_content:
                            full_content = "".join(story_content)
                            content_length = len(full_content)
                            # Log a summary of the content instead of the full content
                            simulation_logger.info(
                                f"Chapter {current_chapter} content complete ({content_length} chars)"
                            )
                            # Log the first 100 chars as a preview
                            preview = (
                                full_content[:100] + "..."
                                if content_length > 100
                                else full_content
                            )
                            simulation_logger.debug(f"Content preview: {preview}")

                            # Still print for human readability during development
                            print_separator("Chapter Content")
                            print(full_content)

                        if choices_data:
                            print_separator("Choices")
                            for i, choice in enumerate(choices_data):
                                print(
                                    f"  {i + 1}. {choice['text']} (ID: {choice['id']})"
                                )

                            # Determine if this is a lesson chapter or story chapter
                            is_lesson_chapter = False
                            if response_state and "current_chapter" in response_state:
                                chapter_info = response_state["current_chapter"]
                                is_lesson_chapter = (
                                    chapter_info.get("chapter_type") == "lesson"
                                )

                                if is_lesson_chapter:
                                    simulation_logger.debug(
                                        "Processing lesson chapter choice"
                                    )
                                    # For lesson chapters, try to find the correct answer
                                    question_data = chapter_info.get("question", {})
                                    if question_data and "answers" in question_data:
                                        # Find the correct answer for logging purposes
                                        correct_answer = next(
                                            (
                                                a
                                                for a in question_data["answers"]
                                                if a.get("is_correct")
                                            ),
                                            None,
                                        )
                                        if correct_answer:
                                            simulation_logger.debug(
                                                f"Correct answer: {correct_answer.get('text')}"
                                            )

                            # Simulate choice selection
                            chosen_choice = random.choice(choices_data)

                            # Log choice selection for automated testing
                            simulation_logger.info(
                                f"CHOICE: Selected '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
                            )

                            # Print for human readability
                            print_separator("Selected Choice")
                            print(
                                f"Selected: '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
                            )

                            # For lesson chapters, log whether the choice was correct
                            if (
                                is_lesson_chapter
                                and "current_chapter" in response_state
                            ):
                                question_data = response_state["current_chapter"].get(
                                    "question", {}
                                )
                                if question_data and "answers" in question_data:
                                    correct_answer = next(
                                        (
                                            a["text"]
                                            for a in question_data["answers"]
                                            if a.get("is_correct")
                                        ),
                                        None,
                                    )
                                    if correct_answer:
                                        is_correct = (
                                            chosen_choice["text"] == correct_answer
                                        )
                                        # Log lesson answer correctness for automated testing
                                        simulation_logger.info(
                                            f"LESSON: Answer is {'CORRECT' if is_correct else 'INCORRECT'} - Selected: '{chosen_choice['text']}', Correct: '{correct_answer}'"
                                        )

                            # Prepare and send choice message
                            choice_message = {
                                "state": response_state
                                or initial_state_message["state"],
                                "choice": {
                                    "chosen_path": chosen_choice["id"],
                                    "choice_text": chosen_choice["text"],
                                },
                            }
                            await websocket.send(json.dumps(choice_message))
                            simulation_logger.debug(
                                f"Sent choice: {json.dumps(choice_message, indent=2)}"
                            )
                            current_chapter += 1
                            if current_chapter > story_length:
                                print_separator("Story Complete")
                                simulation_logger.info(
                                    f"Reached maximum story length of {story_length} chapters. Ending simulation."
                                )
                                return

                    except Exception as e:
                        simulation_logger.error(
                            f"Error during chapter {current_chapter}: {e}"
                        )
                        raise

            finally:
                if websocket:
                    try:
                        await websocket.close()
                    except Exception as e:
                        simulation_logger.debug(f"Error during websocket cleanup: {e}")

        except websockets.exceptions.InvalidStatusCode as e:
            simulation_logger.error(
                f"Failed to connect to WebSocket (attempt {retry + 1}/{MAX_RETRIES}): {e}"
            )
            if retry < MAX_RETRIES - 1 and not should_exit:
                simulation_logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                simulation_logger.error(
                    "Max retries reached or exit requested. Exiting."
                )
                return
        except Exception as e:
            simulation_logger.error(
                f"Unexpected error (attempt {retry + 1}/{MAX_RETRIES}): {e}"
            )
            if retry < MAX_RETRIES - 1 and not should_exit:
                simulation_logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                simulation_logger.error(
                    "Max retries reached or exit requested. Exiting."
                )
                return
        finally:
            if websocket:
                try:
                    await websocket.close()
                except Exception as e:
                    simulation_logger.debug(f"Error during websocket cleanup: {e}")

    simulation_logger.info("Simulation finished.")


if __name__ == "__main__":
    try:
        # Assume FastAPI server is already running
        simulation_logger.info(
            "Assuming FastAPI server is already running at http://localhost:8000"
        )

        # Run the simulation
        asyncio.run(simulate_story())
    except KeyboardInterrupt:
        simulation_logger.info("\nSimulation interrupted by user")
    finally:
        # Ensure we clean up any remaining connections
        if websocket:
            try:
                asyncio.run(websocket.close())
            except Exception as e:
                simulation_logger.debug(f"Error during websocket cleanup: {e}")
