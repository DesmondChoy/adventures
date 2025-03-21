"""
Generate All Chapters for Learning Odyssey

This script simulates a user going through the Learning Odyssey app experience
to generate ten chapters. It randomly selects a story category and lesson topic,
then makes random choices for each chapter to complete the adventure.

Usage:
    python tests/simulations/generate_all_chapters.py [--category CATEGORY] [--topic TOPIC]

Example:
    python tests/simulations/generate_all_chapters.py --category "enchanted_forest_tales" --topic "Singapore History"
"""

import asyncio
import websockets.client
import json
import random
import logging
import urllib.parse
import signal
import sys
import time
import uuid
import os
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, ClassVar
from pydantic import Field

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import app components
from app.models.story import (
    AdventureState,
    ChapterData,
    ChapterType,
    ChapterContent,
    StoryChoice,
)
from app.data.story_loader import StoryLoader
from app.data.lesson_loader import LessonLoader
from app.services.chapter_manager import ChapterManager
from app.utils.logging_config import StructuredLogger

# Constants
STANDARD_TIMEOUT = 30  # seconds for general operations
CONCLUSION_TIMEOUT = 60  # seconds for conclusion chapter
SUMMARY_TIMEOUT = 60  # seconds for summary operations
MAX_RETRIES = 5  # maximum number of connection retries
RETRY_DELAY = 2  # base delay in seconds for exponential backoff
STORY_LENGTH = 10  # fixed story length

# Generate unique run ID and timestamp for this simulation run
run_id = str(uuid.uuid4())[:8]
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"logs/simulations/generate_all_chapters_{timestamp}_{run_id}.log"

# Ensure logs directory exists
os.makedirs("logs/simulations", exist_ok=True)

# Configure logging
logging.setLoggerClass(StructuredLogger)


# Create a custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        if (
            hasattr(record, "msg")
            and isinstance(record.msg, str)
            and record.msg.startswith("{")
        ):
            return record.msg
        return super().format(record)


# Create handlers
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Apply the JsonFormatter to the handlers
json_formatter = JsonFormatter("%(message)s")
file_handler.setFormatter(json_formatter)
console_handler.setFormatter(json_formatter)

# Configure websockets logger to only show warnings and errors
logging.getLogger("websockets").setLevel(logging.WARNING)

# Setup logger
logger = logging.getLogger("generate_all_chapters")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False  # Prevent propagation to avoid duplicate logging

# Write a direct header to the log file
with open(log_filename, "w") as f:
    f.write(f"=== GENERATE ALL CHAPTERS START: {timestamp} (ID: {run_id}) ===\n")
    f.write("This header is written directly to ensure the log file is working.\n")
    f.write("=" * 80 + "\n\n")

# Global variables for cleanup
websocket = None
should_exit = False


def signal_handler(signum, frame):
    """Handle cleanup on interrupt"""
    global should_exit
    logger.info("\nReceived interrupt signal. Cleaning up...")
    should_exit = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class SimulationState(AdventureState):
    """Extended AdventureState for simulation purposes."""

    simulation_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata specific to the simulation run"
    )

    def __init__(self, *args, **kwargs):
        # Initialize with default values
        if "simulation_metadata" not in kwargs:
            kwargs["simulation_metadata"] = {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "random_choices": [],
            }
        super().__init__(*args, **kwargs)

    def record_choice(self, chapter_number: int, choice_text: str, choice_id: str):
        """Record a choice made during simulation."""
        if "random_choices" not in self.simulation_metadata:
            self.simulation_metadata["random_choices"] = []

        self.simulation_metadata["random_choices"].append(
            {
                "chapter_number": chapter_number,
                "choice_text": choice_text,
                "choice_id": choice_id,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(
            "EVENT:CHOICE_SELECTED",
            extra={
                "chapter_number": chapter_number,
                "choice_id": choice_id,
                "choice_text": choice_text,
                "timestamp": datetime.now().isoformat(),
                "run_id": run_id,
            },
        )

    def save_to_file(self, filename=None):
        """Save the entire simulation state to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"logs/simulations/simulation_state_{timestamp}_{run_id}.json"

        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Convert to dictionary for serialization
        state_dict = self.dict()

        # Save to file
        with open(filename, "w") as f:
            json.dump(state_dict, f, indent=2)

        logger.info(f"Saved simulation state to {filename}")
        return filename


def print_separator(title=""):
    """Print a visual separator with optional title."""
    width = 80
    if title:
        padding = (width - len(title) - 2) // 2
        print("\n" + "=" * padding + f" {title} " + "=" * padding)
    else:
        print("\n" + "=" * width)


def load_story_data():
    """Load story data from individual YAML files."""
    try:
        loader = StoryLoader()
        return loader.load_all_stories()
    except Exception as e:
        logger.error(f"Failed to load story data: {e}")
        return {"story_categories": {}}


def load_lesson_data():
    """Load lesson data from CSV files in the lessons directory."""
    try:
        loader = LessonLoader()
        return loader.load_all_lessons()
    except Exception as e:
        logger.error(f"Failed to load lesson data: {e}")
        return None


def get_random_story_category(story_data):
    """Randomly select a story category."""
    categories = list(story_data["story_categories"].keys())
    return random.choice(categories)


def get_random_lesson_topic(lesson_df):
    """Randomly select a lesson topic."""
    topics = lesson_df["topic"].unique()
    return random.choice(topics)


async def establish_websocket_connection(
    uri: str, retry_count: int = 0
) -> Optional[websockets.client.WebSocketClientProtocol]:
    """Establish a WebSocket connection with retry logic."""
    if retry_count >= MAX_RETRIES or should_exit:
        logger.error("Max retries reached or exit requested")
        return None

    try:
        ws = await websockets.connect(uri)
        logger.info("WebSocket connection established")
        return ws
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(
            f"Failed to connect to WebSocket (attempt {retry_count + 1}/{MAX_RETRIES}): {e}"
        )
        if retry_count < MAX_RETRIES - 1 and not should_exit:
            backoff_delay = RETRY_DELAY * (2**retry_count)
            logger.info(f"Retrying in {backoff_delay} seconds...")
            await asyncio.sleep(backoff_delay)
            return await establish_websocket_connection(uri, retry_count + 1)
        else:
            return None
    except Exception as e:
        logger.error(f"Unexpected error during connection: {e}")
        if retry_count < MAX_RETRIES - 1 and not should_exit:
            backoff_delay = RETRY_DELAY * (2**retry_count)
            logger.info(f"Retrying in {backoff_delay} seconds...")
            await asyncio.sleep(backoff_delay)
            return await establish_websocket_connection(uri, retry_count + 1)
        else:
            return None


async def send_message(
    ws: websockets.client.WebSocketClientProtocol, message: Dict[str, Any]
) -> None:
    """Send a message to the WebSocket server."""
    message_json = json.dumps(message)
    await ws.send(message_json)
    logger.debug(f"Sent message: {json.dumps(message, indent=2)}")


async def process_chapter(
    websocket: websockets.client.WebSocketClientProtocol,
    chapter_number: int,
    is_conclusion: bool = False,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Process a single chapter's content and extract choices.

    Args:
        websocket: The WebSocket connection
        chapter_number: The current chapter number
        is_conclusion: Whether this is the conclusion chapter

    Returns:
        Tuple of (chapter_content, choices)
    """
    logger.info(f"Processing chapter {chapter_number}")

    # Initialize variables for story content
    story_content = []
    choices_data = []
    state_data = None

    # Use different timeout based on chapter type
    timeout = CONCLUSION_TIMEOUT if is_conclusion else STANDARD_TIMEOUT

    # Process messages until choices are presented or conclusion is complete
    while True:
        try:
            response_raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)

            try:
                # Try to parse as JSON
                response_data = json.loads(response_raw)

                # Handle different response types
                if isinstance(response_data, dict):
                    response_type = response_data.get("type")

                    if response_type == "chapter_update":
                        # Store state for later use
                        state_data = response_data.get("state", {})

                        # Log chapter type information if available
                        if "current_chapter" in state_data:
                            chapter_info = state_data["current_chapter"]
                            chapter_type = chapter_info.get("chapter_type", "unknown")

                            # Log structured chapter data
                            logger.info(
                                "EVENT:CHAPTER_START",
                                extra={
                                    "chapter_number": chapter_number,
                                    "chapter_type": chapter_type,
                                    "chapter_id": state_data.get("current_chapter_id"),
                                    "timestamp": datetime.now().isoformat(),
                                    "run_id": run_id,
                                },
                            )

                            # If this is a lesson chapter, log question info
                            if chapter_info.get("question"):
                                question_data = chapter_info["question"]
                                logger.info(
                                    "EVENT:LESSON_QUESTION",
                                    extra={
                                        "chapter_number": chapter_number,
                                        "question": question_data.get("question"),
                                        "topic": question_data.get("topic"),
                                        "subtopic": question_data.get("subtopic"),
                                        "answers": json.dumps(
                                            [
                                                a.get("text")
                                                for a in question_data.get(
                                                    "answers", []
                                                )
                                            ]
                                        ),
                                        "correct_answer": next(
                                            (
                                                a.get("text")
                                                for a in question_data.get(
                                                    "answers", []
                                                )
                                                if a.get("is_correct")
                                            ),
                                            None,
                                        ),
                                        "explanation": question_data.get(
                                            "explanation", ""
                                        ),
                                        "timestamp": datetime.now().isoformat(),
                                    },
                                )
                        continue

                    elif response_type == "choices":
                        # Store choices and break the inner loop to process them
                        choices_data = response_data.get("choices", [])

                        # Log choices in a structured format
                        logger.info(
                            "EVENT:CHOICES_PRESENTED",
                            extra={
                                "chapter_number": chapter_number,
                                "choices_count": len(choices_data),
                                "choices": json.dumps(
                                    [
                                        {"text": c.get("text"), "id": c.get("id")}
                                        for c in choices_data
                                    ]
                                ),
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                        break

                    elif response_type == "story_complete":
                        # Handle story completion
                        stats = response_data.get("state", {}).get("stats", {})

                        # Log detailed statistics
                        logger.info(
                            "EVENT:STORY_COMPLETE",
                            extra={
                                "total_lessons": stats.get("total_lessons", 0),
                                "correct_answers": stats.get(
                                    "correct_lesson_answers", 0
                                ),
                                "success_rate": stats.get("completion_percentage", 0),
                                "timestamp": datetime.now().isoformat(),
                                "run_id": run_id,
                                "final_state": json.dumps(
                                    response_data.get("state", {})
                                ),
                            },
                        )

                        # For conclusion chapter, continue receiving content
                        if is_conclusion:
                            continue
                        else:
                            break

                    elif response_type == "hide_loader":
                        # Ignore hide_loader messages
                        continue

                    elif response_type in ["summary_start", "summary_complete"]:
                        # These are handled in process_summary
                        break

            except json.JSONDecodeError:
                # Not JSON, must be story content
                story_content.append(response_raw)

            except Exception as e:
                logger.error(f"Error parsing response: {e}")
                logger.debug(f"Problematic response:\n{response_raw}")

        except asyncio.TimeoutError:
            # For conclusion chapter, timeout might mean content is complete
            if is_conclusion and story_content:
                logger.info(
                    "Timeout while processing conclusion chapter - assuming content complete"
                )
                break
            else:
                logger.error(
                    f"Timeout waiting for response in chapter {chapter_number}"
                )
                raise

        except websockets.exceptions.ConnectionClosed as e:
            # If we're processing the conclusion chapter and the connection closed,
            # it might mean we've received all the content
            if is_conclusion and story_content:
                logger.info(
                    "Connection closed while processing conclusion chapter - assuming content complete"
                )
                break
            else:
                logger.error(
                    f"WebSocket connection closed during chapter {chapter_number}: {e}"
                )
                raise

    # Combine content chunks
    full_content = "".join(story_content)
    content_length = len(full_content)

    # Log chapter completion
    logger.info(f"Chapter {chapter_number} content complete ({content_length} chars)")

    # Print for human readability
    print_separator(f"Chapter {chapter_number} Content")
    print(full_content[:500] + "..." if content_length > 500 else full_content)

    if choices_data:
        print_separator("Choices")
        for i, choice in enumerate(choices_data):
            print(f"  {i + 1}. {choice['text']} (ID: {choice['id']})")

    return full_content, choices_data, state_data


async def process_summary(websocket: websockets.client.WebSocketClientProtocol) -> str:
    """Process the adventure summary.

    Args:
        websocket: The WebSocket connection

    Returns:
        The summary content
    """
    logger.info("Processing adventure summary")

    # Initialize variables for summary content
    summary_content = []
    summary_state = None

    # Process messages until summary is complete
    while True:
        try:
            response_raw = await asyncio.wait_for(
                websocket.recv(), timeout=SUMMARY_TIMEOUT
            )

            try:
                # Try to parse as JSON
                response_data = json.loads(response_raw)

                # Handle different response types
                if isinstance(response_data, dict):
                    response_type = response_data.get("type")

                    if response_type == "summary_start":
                        logger.info("Summary generation started")
                        continue

                    elif response_type == "summary_complete":
                        # Store state for later use
                        summary_state = response_data.get("state", {})

                        # Log summary completion
                        logger.info(
                            "EVENT:SUMMARY_COMPLETE",
                            extra={
                                "timestamp": datetime.now().isoformat(),
                                "run_id": run_id,
                                "chapter_summaries": summary_state.get(
                                    "chapter_summaries", []
                                ),
                            },
                        )
                        break

            except json.JSONDecodeError:
                # Not JSON, must be summary content
                summary_content.append(response_raw)

            except Exception as e:
                logger.error(f"Error parsing summary response: {e}")
                logger.debug(f"Problematic response:\n{response_raw}")

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for summary response")
            break

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed during summary processing: {e}")
            break

    # Combine content chunks
    full_content = "".join(summary_content)
    content_length = len(full_content)

    # Log summary completion
    logger.info(f"Summary content complete ({content_length} chars)")

    # Print for human readability
    print_separator("Summary Content")
    print(full_content[:500] + "..." if content_length > 500 else full_content)

    return full_content, summary_state


async def generate_all_chapters(story_category=None, lesson_topic=None):
    """Generate all chapters for a complete adventure.

    Args:
        story_category: Optional story category to use
        lesson_topic: Optional lesson topic to use

    Returns:
        The completed simulation state
    """
    global websocket, should_exit

    # Record start time for duration calculation
    start_time = time.time()

    # Load data and make random selections
    story_data = load_story_data()
    lesson_df = load_lesson_data()

    if story_category is None:
        story_category = get_random_story_category(story_data)

    if lesson_topic is None:
        lesson_topic = get_random_lesson_topic(lesson_df)

    # Log simulation start with complete metadata
    logger.info(
        "SIMULATION_RUN_START",
        extra={
            "run_id": run_id,
            "timestamp": timestamp,
            "story_category": story_category,
            "lesson_topic": lesson_topic,
            "story_length": STORY_LENGTH,
        },
    )

    print_separator("Story Configuration")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Run ID: {run_id}")
    print(f"Log File: {log_filename}")
    print(f"Category: {story_category}")
    print(f"Topic: {lesson_topic}")
    print(f"Length: {STORY_LENGTH} chapters")
    print(
        f"WebSocket URI: ws://localhost:8000/ws/story/{urllib.parse.quote(story_category)}/{urllib.parse.quote(lesson_topic)}"
    )
    print("=" * 80)

    # Initialize state using ChapterManager
    chapter_manager = ChapterManager()
    adventure_state = chapter_manager.initialize_adventure_state(
        STORY_LENGTH, lesson_topic, story_category
    )

    # Convert to SimulationState
    state = SimulationState(
        current_chapter_id=adventure_state.current_chapter_id,
        story_length=adventure_state.story_length,
        chapters=adventure_state.chapters.copy(),
        planned_chapter_types=adventure_state.planned_chapter_types.copy(),
        current_storytelling_phase=adventure_state.current_storytelling_phase,
        selected_narrative_elements=adventure_state.selected_narrative_elements.copy(),
        selected_sensory_details=adventure_state.selected_sensory_details.copy(),
        selected_theme=adventure_state.selected_theme,
        selected_moral_teaching=adventure_state.selected_moral_teaching,
        selected_plot_twist=adventure_state.selected_plot_twist,
        metadata=adventure_state.metadata.copy(),
        chapter_summaries=adventure_state.chapter_summaries.copy()
        if adventure_state.chapter_summaries
        else [],
    )

    # Connect to WebSocket
    uri = f"ws://localhost:8000/ws/story/{urllib.parse.quote(story_category)}/{urllib.parse.quote(lesson_topic)}"

    try:
        websocket = await establish_websocket_connection(uri)
        if not websocket:
            logger.error("Failed to establish WebSocket connection")
            return None

        # Send initial state message
        initial_state_message = {
            "state": {
                "current_chapter_id": "start",
                "story_length": STORY_LENGTH,
                "chapters": [],
                "selected_narrative_elements": {},
                "selected_sensory_details": {},
                "selected_theme": "",
                "selected_moral_teaching": "",
                "selected_plot_twist": "",
                "planned_chapter_types": [],
                "current_storytelling_phase": "Exposition",
                "chapter_summaries": [],
                "metadata": {},
            }
        }
        await send_message(websocket, initial_state_message)

        # Send 'start' choice to begin story
        start_choice_message = {
            "state": initial_state_message["state"],
            "choice": {"chosen_path": "start", "choice_text": "Start Story"},
        }
        await send_message(websocket, start_choice_message)

        # Process chapters 1-10
        current_chapter = 1

        while current_chapter <= STORY_LENGTH and not should_exit:
            # Process chapter content and choices
            is_conclusion = current_chapter == STORY_LENGTH
            chapter_content, choices, chapter_state = await process_chapter(
                websocket, current_chapter, is_conclusion
            )

            # Create chapter data
            chapter_type = (
                ChapterType.CONCLUSION if is_conclusion else ChapterType.STORY
            )  # Default to STORY

            # Try to get actual chapter type from state
            if chapter_state and "current_chapter" in chapter_state:
                chapter_info = chapter_state["current_chapter"]
                chapter_type_str = chapter_info.get("chapter_type", "story")
                try:
                    chapter_type = ChapterType(chapter_type_str)
                except ValueError:
                    logger.warning(
                        f"Unknown chapter type: {chapter_type_str}, using default"
                    )

            # Create chapter content object
            chapter_content_obj = ChapterContent(
                content=chapter_content,
                choices=[
                    StoryChoice(text=choice["text"], next_chapter=choice["id"])
                    for choice in choices
                ],
            )

            # Create chapter data object
            chapter_data = ChapterData(
                chapter_number=current_chapter,
                content=chapter_content,
                chapter_type=chapter_type,
                response=None,  # Will be set after choice is made
                chapter_content=chapter_content_obj,
                question=chapter_state["current_chapter"].get("question")
                if chapter_state and "current_chapter" in chapter_state
                else None,
            )

            # Add chapter to state
            state.chapters.append(chapter_data)

            # If this is the conclusion chapter, we're done with chapters
            if is_conclusion:
                logger.info("Conclusion chapter processed")

                # Send reveal_summary choice
                reveal_summary_message = {
                    "state": chapter_state,
                    "choice": {
                        "chosen_path": "reveal_summary",
                        "choice_text": "Reveal Your Adventure Summary",
                    },
                }
                await send_message(websocket, reveal_summary_message)

                # Process summary
                summary_content, summary_state = await process_summary(websocket)

                # Update chapter summaries in state
                if summary_state and "chapter_summaries" in summary_state:
                    state.chapter_summaries = summary_state["chapter_summaries"]
                    logger.info(
                        f"Updated state with {len(state.chapter_summaries)} chapter summaries"
                    )

                # Create summary chapter
                summary_chapter = ChapterData(
                    chapter_number=current_chapter + 1,
                    content=summary_content,
                    chapter_type=ChapterType.SUMMARY,
                    response=None,
                    chapter_content=ChapterContent(content=summary_content, choices=[]),
                    question=None,
                )

                # Add summary chapter to state
                state.chapters.append(summary_chapter)

                break

            # Make random choice
            if choices:
                chosen_choice = random.choice(choices)

                # Record choice in state
                state.record_choice(
                    current_chapter, chosen_choice["text"], chosen_choice["id"]
                )

                # Print for human readability
                print_separator("Selected Choice")
                print(
                    f"Selected: '{chosen_choice['text']}' (ID: {chosen_choice['id']})"
                )

                # For lesson chapters, log whether the choice was correct
                if chapter_type == ChapterType.LESSON and chapter_data.question:
                    correct_answer = next(
                        (
                            a["text"]
                            for a in chapter_data.question["answers"]
                            if a.get("is_correct")
                        ),
                        None,
                    )
                    if correct_answer:
                        is_correct = chosen_choice["text"] == correct_answer
                        # Log lesson answer correctness
                        logger.info(
                            "EVENT:LESSON_ANSWER",
                            extra={
                                "chapter_number": current_chapter,
                                "is_correct": is_correct,
                                "selected_answer": chosen_choice["text"],
                                "correct_answer": correct_answer,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                # Send choice message
                choice_message = {
                    "state": chapter_state,
                    "choice": {
                        "chosen_path": chosen_choice["id"],
                        "choice_text": chosen_choice["text"],
                    },
                }
                await send_message(websocket, choice_message)

                # Move to next chapter
                current_chapter += 1
            else:
                logger.error(f"No choices available for chapter {current_chapter}")
                break

    except Exception as e:
        logger.error(f"Error during chapter generation: {e}")

    finally:
        # Close WebSocket connection
        if websocket:
            try:
                await websocket.close()
            except Exception as e:
                logger.debug(f"Error during websocket cleanup: {e}")

    # Save final state
    state_file = state.save_to_file()

    # Log simulation end with summary statistics
    logger.info(
        "SIMULATION_RUN_END",
        extra={
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "story_category": story_category,
            "lesson_topic": lesson_topic,
            "story_length": STORY_LENGTH,
            "duration_seconds": time.time() - start_time,
            "chapters_generated": len(state.chapters),
            "state_file": state_file,
        },
    )

    logger.info(f"Simulation finished. Log file: {log_filename}")

    return state


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate all chapters for a story")
    parser.add_argument("--category", type=str, help="Specify story category")
    parser.add_argument("--topic", type=str, help="Specify lesson topic")
    args = parser.parse_args()

    try:
        # Run the simulation
        asyncio.run(generate_all_chapters(args.category, args.topic))
    except KeyboardInterrupt:
        logger.info("\nSimulation interrupted by user")
    finally:
        # Ensure we clean up any remaining connections
        if websocket:
            try:
                asyncio.run(websocket.close())
            except Exception as e:
                logger.debug(f"Error during websocket cleanup: {e}")
