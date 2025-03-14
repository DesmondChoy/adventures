"""
Story simulation for WebSocket router and service integration.

This simulation serves two purposes:
1. Primary: Generate structured log data that captures a complete user journey
   through the application, which will be analyzed by dedicated test files.
2. Secondary: Verify that the end-to-end workflow executes successfully.

The simulation exercises both:
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

The simulation produces comprehensive logs with standardized prefixes that make it easy
to verify specific behaviors in subsequent test runs. It is not a test suite itself,
but rather a data generation tool that enables more specific testing.

Updates (2025-02-25):
- Fixed file path for story data (new_stories.yaml)
- Updated initial state structure to match AdventureStateManager expectations
- Enhanced response handling for different message types
- Added support for lesson chapter detection and answer validation
- Improved logging for chapter types and question handling
- Fixed story length to match codebase (constant 10 chapters)
- Optimized for automated testing by removing real-time content streaming
- Enhanced logging for better test analysis and debugging

Updates (2025-03-11):
- Added support for the new chapter summaries approach
- Updated initial state to include chapter_summaries field
- Added detection and logging of chapter summaries as they're generated
- Added structured logging for chapter summary events
- Added comprehensive summary log at the end of simulation
- Enhanced human-readable output with chapter summary display

Usage Instructions:
1. Prerequisites:
   - Ensure the FastAPI server is running at http://localhost:8000
   - Verify that story data and lesson data are properly loaded

2. Basic Execution:
   $ python tests/simulations/story_simulation.py

3. Command-line Options:
   - Specify a story category:
     $ python tests/simulations/story_simulation.py --category "enchanted_forest_tales"
   - Specify a lesson topic:
     $ python tests/simulations/story_simulation.py --topic "Singapore History"
   - Output only the run ID (useful for test scripts):
     $ python tests/simulations/story_simulation.py --output-run-id

4. Output:
   - Simulation progress is displayed in the console
   - Detailed logs are written to logs/simulations/simulation_[DATE]_[RUN_ID].log
   - Chapter summaries are logged with the prefix "EVENT:CHAPTER_SUMMARY"
   - Final comprehensive summary with all chapters is logged as "EVENT:ALL_CHAPTER_SUMMARIES"

5. Working with Chapter Summaries:
   - Chapter summaries are automatically captured in the log file
   - Extract them from the "EVENT:ALL_CHAPTER_SUMMARIES" log entry
   - Use the summaries to test the SUMMARY chapter implementation independently
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
import sys
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


import uuid
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now we can import from app
from app.utils.logging_config import StructuredLogger

# Generate unique run ID and timestamp for this simulation run
run_id = str(uuid.uuid4())[:8]
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"logs/simulations/simulation_{timestamp}_{run_id}.log"

# Ensure logs directory exists
os.makedirs("logs/simulations", exist_ok=True)

# Configure logging - use the StructuredLogger properly
logging.setLoggerClass(StructuredLogger)


# Create a custom JSON formatter that doesn't interfere with StructuredLogger's formatting
class JsonPassthroughFormatter(logging.Formatter):
    def format(self, record):
        # Just return the message as is if it's already JSON formatted
        if (
            hasattr(record, "msg")
            and isinstance(record.msg, str)
            and record.msg.startswith("{")
        ):
            return record.msg
        # For debug logs from chapter_manager.py, ensure they're properly formatted
        if (
            hasattr(record, "name")
            and record.name == "story_app"
            and hasattr(record, "levelname")
            and record.levelname == "DEBUG"
        ):
            # Include the original message in the formatted output
            return f"{record.getMessage()}"
        # Otherwise use the default formatter
        return super().format(record)


# Create handlers
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Apply the JsonPassthroughFormatter to the handlers
json_formatter = JsonPassthroughFormatter("%(message)s")
file_handler.setFormatter(json_formatter)
console_handler.setFormatter(json_formatter)

# Configure websockets logger to only show warnings and errors
logging.getLogger("websockets").setLevel(logging.WARNING)

# Setup story_app logger
logger = logging.getLogger("story_app")
logger.setLevel(logging.DEBUG)
# Add handlers to story_app logger to capture logs from chapter_manager.py
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Setup simulation logger with the new handlers
simulation_logger = logging.getLogger(f"simulation.{run_id}")
simulation_logger.setLevel(logging.DEBUG)
simulation_logger.addHandler(file_handler)
simulation_logger.addHandler(console_handler)
simulation_logger.propagate = False  # Prevent propagation to avoid duplicate logging

# Write a direct header to the log file to ensure it's working
with open(log_filename, "w") as f:
    f.write(f"=== SIMULATION RUN START: {timestamp} (ID: {run_id}) ===\n")
    f.write("This header is written directly to ensure the log file is working.\n")
    f.write("Subsequent logs will be written through the logging system.\n")
    f.write("=" * 80 + "\n\n")

# Constants
MAX_RETRIES = 5  # Increased from 3 to 5
RETRY_DELAY = 2  # Base delay in seconds for exponential backoff
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
    """Load story data from individual YAML files."""
    try:
        # Import here to avoid circular imports
        sys.path.insert(
            0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        )
        from app.data.story_loader import StoryLoader

        loader = StoryLoader()
        return loader.load_all_stories()
    except Exception as e:
        simulation_logger.error(f"Failed to load story data: {e}")
        return {"story_categories": {}}


def load_lesson_data():
    """Load lesson data from CSV files in the lessons directory."""
    try:
        # Import here to avoid circular imports
        sys.path.insert(
            0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        )
        from app.data.lesson_loader import LessonLoader

        loader = LessonLoader()
        return loader.load_all_lessons()
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

    # Log simulation start with complete metadata
    simulation_logger.info(
        "SIMULATION_RUN_START",
        extra={
            "run_id": run_id,
            "timestamp": timestamp,
            "story_category": story_category,
            "lesson_topic": lesson_topic,
            "story_length": story_length,
        },
    )

    print_separator("Story Configuration")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Run ID: {run_id}")
    print(f"Log File: {log_filename}")
    print(f"Category: {story_category}")
    print(f"Topic: {lesson_topic}")
    print(f"Length: {story_length} chapters")
    print(
        f"WebSocket URI: ws://localhost:8000/ws/story/{urllib.parse.quote(story_category)}/{urllib.parse.quote(lesson_topic)}"
    )
    print("=" * 80)

    # Log configuration with run_id for traceability
    simulation_logger.debug(
        f"Starting story simulation with: Category='{story_category}', Topic='{lesson_topic}', Length={story_length} chapters",
        extra={"run_id": run_id},
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
                        "chapter_summaries": [],  # Added for the new summary approach
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

                                        # Handle different response types
                                        response_type = response_data.get("type")

                                        if response_type == "chapter_update":
                                            # Store state for later use
                                            response_state = response_data.get(
                                                "state", {}
                                            )

                                            # Check for chapter summaries in the state
                                            if "chapter_summaries" in response_state:
                                                chapter_summaries = response_state[
                                                    "chapter_summaries"
                                                ]
                                                if chapter_summaries:
                                                    simulation_logger.info(
                                                        "EVENT:CHAPTER_SUMMARIES_UPDATED",
                                                        extra={
                                                            "chapter_number": current_chapter,
                                                            "summaries_count": len(
                                                                chapter_summaries
                                                            ),
                                                            "timestamp": datetime.now().isoformat(),
                                                            "run_id": run_id,
                                                        },
                                                    )

                                                    # Log each individual summary
                                                    for i, summary in enumerate(
                                                        chapter_summaries, 1
                                                    ):
                                                        if (
                                                            i <= current_chapter
                                                        ):  # Only log summaries for completed chapters
                                                            simulation_logger.info(
                                                                "EVENT:CHAPTER_SUMMARY",
                                                                extra={
                                                                    "chapter_number": i,
                                                                    "summary": summary,
                                                                    "timestamp": datetime.now().isoformat(),
                                                                    "run_id": run_id,
                                                                },
                                                            )

                                            # Log chapter type information if available
                                            if "current_chapter" in response_state:
                                                chapter_info = response_state[
                                                    "current_chapter"
                                                ]
                                                chapter_type = chapter_info.get(
                                                    "chapter_type", "unknown"
                                                )

                                                # Log structured chapter data for automated testing
                                                simulation_logger.info(
                                                    "EVENT:CHAPTER_START",
                                                    extra={
                                                        "chapter_number": current_chapter,
                                                        "chapter_type": chapter_type,
                                                        "chapter_id": response_state.get(
                                                            "current_chapter_id"
                                                        ),
                                                        "timestamp": datetime.now().isoformat(),
                                                        "run_id": run_id,
                                                    },
                                                )

                                                # Log state transition
                                                simulation_logger.info(
                                                    "EVENT:STATE_TRANSITION",
                                                    extra={
                                                        "from_chapter": initial_state_message[
                                                            "state"
                                                        ].get("current_chapter_id")
                                                        if current_chapter == 1
                                                        else "previous_chapter",
                                                        "to_chapter": response_state.get(
                                                            "current_chapter_id"
                                                        ),
                                                        "state": json.dumps(
                                                            response_state
                                                        ),
                                                        "timestamp": datetime.now().isoformat(),
                                                    },
                                                )

                                                # If this is a lesson chapter, log question info
                                                if chapter_info.get("question"):
                                                    question_data = chapter_info[
                                                        "question"
                                                    ]
                                                    simulation_logger.info(
                                                        "EVENT:LESSON_QUESTION",
                                                        extra={
                                                            "chapter_number": current_chapter,
                                                            "question": question_data.get(
                                                                "question"
                                                            ),
                                                            "topic": question_data.get(
                                                                "topic"
                                                            ),
                                                            "subtopic": question_data.get(
                                                                "subtopic"
                                                            ),
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
                                                                    if a.get(
                                                                        "is_correct"
                                                                    )
                                                                ),
                                                                None,
                                                            ),
                                                            "timestamp": datetime.now().isoformat(),
                                                        },
                                                    )

                                                    # Log process execution for lesson processing
                                                    simulation_logger.info(
                                                        "EVENT:PROCESS_START",
                                                        extra={
                                                            "process_name": "process_lesson",
                                                            "chapter_number": current_chapter,
                                                            "chapter_type": chapter_type,
                                                            "timestamp": datetime.now().isoformat(),
                                                        },
                                                    )
                                            continue

                                        elif response_type == "choices":
                                            # Store choices and break the inner loop to process them
                                            choices_data = response_data.get(
                                                "choices", []
                                            )

                                            # Log choices in a structured format for testing
                                            simulation_logger.info(
                                                "EVENT:CHOICES_PRESENTED",
                                                extra={
                                                    "chapter_number": current_chapter,
                                                    "choices_count": len(choices_data),
                                                    "choices": json.dumps(
                                                        [
                                                            {
                                                                "text": c.get("text"),
                                                                "id": c.get("id"),
                                                            }
                                                            for c in choices_data
                                                        ]
                                                    ),
                                                    "timestamp": datetime.now().isoformat(),
                                                },
                                            )
                                            break

                                        elif response_type == "story_complete":
                                            # Handle story completion
                                            stats = response_data.get("state", {}).get(
                                                "stats", {}
                                            )

                                            # First, log the accumulated story content for the final chapter
                                            if story_content:
                                                full_content = "".join(story_content)
                                                content_length = len(full_content)
                                                # Log the final chapter content
                                                simulation_logger.info(
                                                    f"Chapter {current_chapter} content complete ({content_length} chars)"
                                                )
                                                # Log the first 100 chars as a preview
                                                preview = (
                                                    full_content[:100] + "..."
                                                    if content_length > 100
                                                    else full_content
                                                )
                                                simulation_logger.debug(
                                                    f"Content preview: {preview}"
                                                )

                                                # Log the full content for the final chapter
                                                simulation_logger.debug(
                                                    f"Final chapter content: {full_content}"
                                                )

                                                # Print for human readability
                                                print_separator("Final Chapter Content")
                                                print(full_content)

                                            # Log detailed statistics in structured format for automated testing
                                            simulation_logger.info(
                                                "EVENT:STORY_COMPLETE",
                                                extra={
                                                    "total_lessons": stats.get(
                                                        "total_lessons", 0
                                                    ),
                                                    "correct_answers": stats.get(
                                                        "correct_lesson_answers", 0
                                                    ),
                                                    "success_rate": stats.get(
                                                        "completion_percentage", 0
                                                    ),
                                                    "timestamp": datetime.now().isoformat(),
                                                    "run_id": run_id,
                                                    "final_state": json.dumps(
                                                        response_data.get("state", {})
                                                    ),
                                                },
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
                                    # Don't log each chunk to reduce noise - we'll log a summary later
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

                            # Log choice selection in structured format for automated testing
                            simulation_logger.info(
                                "EVENT:CHOICE_SELECTED",
                                extra={
                                    "chapter_number": current_chapter,
                                    "choice_id": chosen_choice["id"],
                                    "choice_text": chosen_choice["text"],
                                    "timestamp": datetime.now().isoformat(),
                                    "run_id": run_id,
                                },
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
                                        # Log lesson answer correctness in structured format
                                        simulation_logger.info(
                                            "EVENT:LESSON_ANSWER",
                                            extra={
                                                "chapter_number": current_chapter,
                                                "is_correct": is_correct,
                                                "selected_answer": chosen_choice[
                                                    "text"
                                                ],
                                                "correct_answer": correct_answer,
                                                "timestamp": datetime.now().isoformat(),
                                            },
                                        )

                                        # Log process execution for consequences
                                        simulation_logger.info(
                                            "EVENT:PROCESS_START",
                                            extra={
                                                "process_name": "process_consequences",
                                                "chapter_number": current_chapter,
                                                "chapter_type": "lesson",
                                                "timestamp": datetime.now().isoformat(),
                                            },
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
                backoff_delay = RETRY_DELAY * (2**retry)
                simulation_logger.info(f"Retrying in {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
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
                backoff_delay = RETRY_DELAY * (2**retry)
                simulation_logger.info(f"Retrying in {backoff_delay} seconds...")
                await asyncio.sleep(backoff_delay)
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

    # Log all chapter summaries at the end for easy extraction
    if response_state and "chapter_summaries" in response_state:
        chapter_summaries = response_state["chapter_summaries"]
        if chapter_summaries:
            # Create a comprehensive log of all summaries for easy extraction
            simulation_logger.info(
                "EVENT:ALL_CHAPTER_SUMMARIES",
                extra={
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(),
                    "story_category": story_category,
                    "lesson_topic": lesson_topic,
                    "summaries_count": len(chapter_summaries),
                    "chapter_summaries": chapter_summaries,
                },
            )

            # Print summaries for human readability
            print_separator("Chapter Summaries")
            for i, summary in enumerate(chapter_summaries, 1):
                print(f"Chapter {i} Summary:")
                print(f"{summary}")
                print("-" * 40)

    # Log simulation end with summary statistics
    simulation_logger.info(
        "SIMULATION_RUN_END",
        extra={
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "story_category": story_category,
            "lesson_topic": lesson_topic,
            "story_length": story_length,
            "duration_seconds": time.time() - start_time,
        },
    )

    simulation_logger.info(f"Simulation finished. Log file: {log_filename}")


if __name__ == "__main__":
    import argparse

    # Add command-line arguments for test integration
    parser = argparse.ArgumentParser(description="Run story simulation")
    parser.add_argument(
        "--output-run-id",
        action="store_true",
        help="Output only the run ID to stdout for test scripts",
    )
    parser.add_argument("--category", type=str, help="Specify story category")
    parser.add_argument("--topic", type=str, help="Specify lesson topic")
    args = parser.parse_args()

    # If test script just needs the run ID
    if args.output_run_id:
        print(run_id)
        sys.exit(0)

    try:
        # Record start time for duration calculation
        start_time = time.time()

        # Assume FastAPI server is already running
        simulation_logger.info(
            "Assuming FastAPI server is already running at http://localhost:8000",
            extra={"run_id": run_id},
        )

        # Run the simulation
        asyncio.run(simulate_story())
    except KeyboardInterrupt:
        simulation_logger.info(
            "\nSimulation interrupted by user", extra={"run_id": run_id}
        )
    finally:
        # Ensure we clean up any remaining connections
        if websocket:
            try:
                asyncio.run(websocket.close())
            except Exception as e:
                simulation_logger.debug(
                    f"Error during websocket cleanup: {e}", extra={"run_id": run_id}
                )
