import asyncio
import websockets
import json
import random
import yaml
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_story_data():
    """Load story data from YAML file."""
    try:
        with open("app/data/stories.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load story data: {e}")
        return {"story_categories": {}}


def load_lesson_data():
    """Load lesson data from CSV file."""
    try:
        return pd.read_csv("app/data/lessons.csv")
    except Exception as e:
        logger.error(f"Failed to load lesson data: {e}")
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
    story_lengths = [3, 5, 7]  # Mirror available options in index.html
    return random.choice(story_lengths)


async def simulate_story():
    # Load data and make random selections
    story_data = load_story_data()
    lesson_df = load_lesson_data()

    story_category = get_random_story_category(story_data)
    lesson_topic = get_random_lesson_topic(lesson_df)
    story_length = get_random_story_length()

    logger.info(
        f"Simulated user selected: Category='{story_category}', Topic='{lesson_topic}', Length={story_length} chapters"
    )

    # Connect to WebSocket
    uri = f"ws://localhost:8000/ws/story/{story_category}/{lesson_topic}"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info("WebSocket connection established.")

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
                }
            }
            await websocket.send(json.dumps(initial_state_message))
            logger.debug(f"Sent initial state: {initial_state_message}")

            # Send 'start' choice to begin story
            start_choice_message = {"choice": "start"}
            await websocket.send(json.dumps(start_choice_message))
            logger.debug(f"Sent start choice: {start_choice_message}")

            # Chapter generation loop
            for chapter_num in range(1, 5):  # Generate 4 chapters
                logger.info(f"\n========== Chapter {chapter_num} ==========")

                try:
                    # Receive chapter update (content and choices)
                    response_json = await websocket.recv()
                    response_data = json.loads(response_json)
                    logger.debug(f"Received message: {response_data.get('type')}")

                    if response_data.get("type") == "chapter_update":
                        chapter_content = response_data["state"]["current_chapter"][
                            "chapter_content"
                        ]["content"]
                        choices_data = response_data.get("choices")

                        if not choices_data:
                            choices_data_json = (
                                await websocket.recv()
                            )  # Wait for choices message if separate
                            choices_data = json.loads(choices_data_json).get("choices")

                        print("\n===== Chapter Content ======")
                        print(chapter_content)

                        if choices_data:
                            print("\n===== Choices ======")
                            for i, choice in enumerate(choices_data):
                                print(
                                    f"  {i + 1}. {choice['text']} (ID: {choice['id']})"
                                )

                            # Simulate choice selection
                            if (
                                response_data["state"]["current_chapter"][
                                    "chapter_type"
                                ]
                                == "lesson"
                            ):
                                chosen_choice = choices_data[
                                    0
                                ]  # Pick first choice for lessons
                                logger.info(
                                    f"Simulating LESSON choice: '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
                                )
                            else:
                                chosen_choice = random.choice(choices_data)
                                logger.info(
                                    f"Simulating STORY choice: '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
                                )

                            choice_message = {
                                "choice": {
                                    "chosen_path": chosen_choice["id"],
                                    "choice_text": chosen_choice["text"],
                                }
                            }
                            await websocket.send(json.dumps(choice_message))
                            logger.debug(f"Sent choice: {choice_message}")
                        else:
                            logger.warning(
                                "No choices received for this chapter (possibly last chapter)."
                            )
                            break

                    elif response_data.get("type") == "story_complete":
                        logger.info("\nStory completed successfully!")
                        stats = response_data["state"]["stats"]
                        print("\n===== Story Stats =====")
                        print(f"  Total Lessons: {stats['total_lessons']}")
                        print(f"  Correct Answers: {stats['correct_lesson_answers']}")
                        print(f"  Success Rate: {stats['completion_percentage']}%")
                        break
                    else:
                        logger.warning(
                            f"Unexpected message type received: {response_data.get('type')}"
                        )
                        break

                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket connection closed unexpectedly")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error during chapter simulation: {e}")
                    break

    except websockets.exceptions.ConnectionError:
        logger.error(
            "Failed to connect to WebSocket server. Is the FastAPI application running?"
        )
    except Exception as e:
        logger.error(f"Unexpected error during simulation: {e}")

    logger.info("Simulation finished.")


if __name__ == "__main__":
    asyncio.run(simulate_story())
