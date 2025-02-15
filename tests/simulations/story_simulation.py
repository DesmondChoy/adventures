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
        with open("app/data/stories.yaml", "r") as f:
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


def get_random_story_length():
    """Randomly select a story length."""
    story_lengths = [5, 5, 5]  # Mirror available options in index.html
    return random.choice(story_lengths)


async def simulate_story():
    global websocket, should_exit

    # Load data and make random selections
    story_data = load_story_data()
    lesson_df = load_lesson_data()

    story_category = get_random_story_category(story_data)
    lesson_topic = get_random_lesson_topic(lesson_df)
    story_length = get_random_story_length()

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
                initial_state_message = {
                    "state": {
                        "current_chapter_id": "start",
                        "current_chapter_number": 0,
                        "story_choices": [],
                        "correct_lesson_answers": 0,
                        "total_lessons": 0,
                        "previous_chapter_content": "",
                        "story_length": story_length,
                        "chapters": [],
                        "story_category": story_category,  # Add story category
                        "lesson_topic": lesson_topic,  # Add lesson topic
                        "story_length_num": story_length,  # Add story length (numerical for easier processing if needed)
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

                                        if (
                                            response_data.get("type")
                                            == "chapter_update"
                                        ):
                                            response_state = response_data.get(
                                                "state", {}
                                            )
                                            continue
                                        elif response_data.get("type") == "choices":
                                            choices_data = response_data.get(
                                                "choices", []
                                            )
                                            break
                                        elif (
                                            response_data.get("type")
                                            == "story_complete"
                                        ):
                                            print_separator("Story Complete")
                                            stats = response_data.get("state", {}).get(
                                                "stats", {}
                                            )
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
                                    print(response_raw, end="", flush=True)
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

                        # Print accumulated story content
                        if story_content:
                            print_separator("Chapter Content")
                            full_content = "".join(story_content)
                            print(full_content)

                        if choices_data:
                            print_separator("Choices")
                            for i, choice in enumerate(choices_data):
                                print(
                                    f"  {i + 1}. {choice['text']} (ID: {choice['id']})"
                                )

                            # Simulate choice selection
                            chosen_choice = random.choice(choices_data)
                            print_separator("Selected Choice")
                            print(
                                f"Selected: '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
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
