from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.story import (
    AdventureState,
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    StoryChoice,
)
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.init_data import sample_question
import yaml
import pandas as pd
import asyncio
import re
import logging
from functools import lru_cache
import random

router = APIRouter()
llm_service = LLMService()
chapter_manager = ChapterManager()
logger = logging.getLogger("story_app")


# Cache for story and lesson data
@lru_cache(maxsize=1)
def load_story_data():
    with open("app/data/stories.yaml", "r") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_lesson_data():
    return pd.read_csv("app/data/lessons.csv")


# Constants for streaming optimization
WORD_BATCH_SIZE = 5  # Number of words to send at once
WORD_DELAY = 0.02  # Reduced delay between word batches
PARAGRAPH_DELAY = 0.1  # Reduced delay between paragraphs


def determine_chapter_types(
    story_length: int, available_questions: int
) -> list[ChapterType]:
    """Determine the sequence of chapter types for the entire story up front.

    Args:
        story_length: Total number of chapters in the story
        available_questions: Number of available questions in the database for the topic

    Returns:
        List of ChapterType values representing the type of each chapter

    Raises:
        ValueError: If there aren't enough questions for the required lessons
    """
    # First and last chapters must be lessons, so we need at least 2 questions
    if available_questions < 2:
        raise ValueError(
            f"Need at least 2 questions, but only have {available_questions}"
        )

    # Initialize with all chapters as STORY type
    chapter_types = [ChapterType.STORY] * story_length

    # First and last chapters are always lessons
    chapter_types[0] = ChapterType.LESSON
    chapter_types[-1] = ChapterType.LESSON

    # Calculate how many more lesson chapters we can add
    remaining_questions = available_questions - 2  # subtract first and last lessons
    if remaining_questions > 0:
        # Get positions for potential additional lessons (excluding first and last positions)
        available_positions = list(range(1, story_length - 1))
        # Randomly select positions for additional lessons, up to the number of remaining questions
        num_additional_lessons = min(remaining_questions, len(available_positions))
        lesson_positions = random.sample(available_positions, num_additional_lessons)

        # Set selected positions to LESSON type
        for pos in lesson_positions:
            chapter_types[pos] = ChapterType.LESSON

    return chapter_types


async def generate_chapter(
    story_category: str,
    lesson_topic: str,
    state: AdventureState,
) -> ChapterContent:
    """Generate a complete chapter with content and choices.

    This function orchestrates the story generation process by:
    1. Loading the appropriate story configuration and lesson data
    2. Using the LLM service to generate the story content as a stream
    3. Processing the streamed content into a complete chapter
    4. Adding appropriate choices based on the story state

    Args:
        story_category: The category of story being generated
        lesson_topic: The educational topic being covered
        state: The current state of the story session

    Returns:
        ChapterContent: A complete chapter with content and choices
    """
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Get the chapter type from the story configuration based on the current chapter
    current_chapter_number = len(state.chapters) + 1
    chapter_type = story_config["chapter_types"][current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)  # Convert string to enum if needed

    # Initialize variables
    story_content = ""
    question = None
    previous_lessons = []

    # Get previous lessons from chapter history
    previous_lessons = [
        LessonResponse(
            question=chapter.response.question,
            chosen_answer=chapter.response.chosen_answer,
            is_correct=chapter.response.is_correct,
        )
        for chapter in state.chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response
    ]

    if previous_lessons:
        logger.debug("\nDEBUG: Previous lessons history:")
        for i, pl in enumerate(previous_lessons, 1):
            logger.debug(f"Lesson {i}: {pl.question['question']}")
            logger.debug(f"Chosen: {pl.chosen_answer} (Correct: {pl.is_correct})")

    # Load new question if at lesson chapter
    if chapter_type == ChapterType.LESSON:
        try:
            # Get list of previously asked questions from chapter history
            used_questions = [
                chapter.response.question["question"]
                for chapter in state.chapters
                if chapter.chapter_type == ChapterType.LESSON and chapter.response
            ]
            # Sample a new question
            question = sample_question(lesson_topic, exclude_questions=used_questions)
            logger.debug(f"DEBUG: Selected question: {question['question']}")
            logger.debug(f"DEBUG: Answers: {question['answers']}")
        except ValueError as e:
            logger.error(f"Error sampling question: {e}")
            raise

    # Generate story content
    try:
        async for chunk in llm_service.generate_story_stream(
            story_config,
            state,
            question,
            previous_lessons,
        ):
            story_content += chunk
    except Exception as e:
        logger.error("\n=== ERROR: LLM Request Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("===============================\n")
        raise

    # Extract choices based on chapter type
    if chapter_type == ChapterType.LESSON and question:
        # Create choices from randomized answers
        story_choices = []
        for answer in question["answers"]:
            story_choices.append(
                StoryChoice(
                    text=answer["text"],
                    next_chapter="correct"
                    if answer["is_correct"]
                    else f"wrong{len(story_choices) + 1}",
                )
            )
    else:
        # Extract structured choices from the story content
        try:
            # Find the choices section
            choices_start = story_content.find("<CHOICES>")
            choices_end = story_content.find("</CHOICES>")

            if choices_start == -1 or choices_end == -1:
                raise ValueError("Could not find choice markers in story content")

            # Extract and clean up the choices section
            choices_text = story_content[choices_start:choices_end].strip()
            # Remove the choices section from the main content
            story_content = story_content[:choices_start].strip()

            # Parse choices using regex
            choice_pattern = r"Choice ([ABC]): (.+)$"
            choices = []

            for line in choices_text.split("\n"):
                match = re.search(choice_pattern, line.strip())
                if match:
                    choices.append(match.group(2).strip())

            if len(choices) != 3:
                raise ValueError("Must have exactly 3 story choices")

            # Create StoryChoice objects
            story_choices = [
                StoryChoice(
                    text=choice_text,
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i, choice_text in enumerate(choices)
            ]
        except Exception as e:
            logger.error(f"Error parsing choices: {e}")
            # Fallback to generic choices if parsing fails
            story_choices = [
                StoryChoice(
                    text=f"Continue with option {i + 1}",
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i in range(3)
            ]

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_chapter: {choice.next_chapter})")
    logger.debug("========================\n")

    return ChapterContent(content=story_content, choices=story_choices)


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()
    state = None

    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()

            # Initialize or update state from client message
            if "state" in data:
                validated_state = data["state"]
                if not state:
                    total_chapters = validated_state["story_length"]
                    story_category_log = validated_state.get(
                        "story_category", "N/A"
                    )  # Extract story_category
                    lesson_topic_log = validated_state.get(
                        "lesson_topic", "N/A"
                    )  # Extract lesson_topic
                    story_length_log = validated_state.get(
                        "story_length_num", "N/A"
                    )  # Extract story_length_num

                    logger.debug(
                        "=== Story Configuration ==="
                    )  # Log using story_app logger
                    logger.debug(f"Category: {story_category_log}")
                    logger.debug(f"Topic: {lesson_topic_log}")
                    logger.debug(f"Length: {story_length_log} chapters")
                    logger.debug("=============================")

                    try:
                        # Use ChapterManager to handle initialization logic
                        available_questions = chapter_manager.count_available_questions(
                            lesson_topic
                        )
                        chapter_types = chapter_manager.determine_chapter_types(
                            total_chapters, available_questions
                        )

                        # Store chapter types in story configuration
                        story_data = load_story_data()
                        story_config = story_data["story_categories"][story_category]
                        story_config["chapter_types"] = chapter_types

                        # Initialize state using ChapterManager
                        state = chapter_manager.initialize_adventure_state(
                            total_chapters, chapter_types
                        )

                    except ValueError as e:
                        await websocket.send_text(str(e))
                        break
                else:
                    # Update existing state from validated chapters
                    if "chapters" in validated_state:
                        # Convert the raw chapter data back into ChapterData objects
                        chapters = []
                        for chapter_data in validated_state["chapters"]:
                            chapter_type = ChapterType(chapter_data["chapter_type"])

                            # Create the appropriate response object if it exists
                            response = None
                            if "response" in chapter_data and chapter_data["response"]:
                                if chapter_type == ChapterType.STORY:
                                    response = StoryResponse(
                                        chosen_path=chapter_data["response"][
                                            "chosen_path"
                                        ],
                                        choice_text=chapter_data["response"][
                                            "choice_text"
                                        ],
                                    )
                                else:  # ChapterType.LESSON
                                    response = LessonResponse(
                                        question=chapter_data["response"]["question"],
                                        chosen_answer=chapter_data["response"][
                                            "chosen_answer"
                                        ],
                                        is_correct=chapter_data["response"][
                                            "is_correct"
                                        ],
                                    )

                            # Create ChapterContent object
                            chapter_content = ChapterContent(
                                content=chapter_data["content"],
                                choices=[
                                    StoryChoice(**choice)
                                    for choice in chapter_data["chapter_content"][
                                        "choices"
                                    ]
                                ],
                            )

                            # Create and append ChapterData
                            chapters.append(
                                ChapterData(
                                    chapter_number=len(chapters) + 1,
                                    content=chapter_data["content"],
                                    chapter_type=chapter_type,
                                    response=response,
                                    chapter_content=chapter_content,
                                )
                            )

                        # Update state with new chapters and current_chapter_id
                        state.chapters = chapters
                        state.current_chapter_id = validated_state.get(
                            "current_chapter_id", "start"
                        )

            choice_data = data.get("choice")
            if choice_data is None:
                continue

            # Extract both chosen_path and choice_text from choice
            if isinstance(choice_data, dict):
                chosen_path = choice_data.get("chosen_path", "")
                choice_text = choice_data.get("choice_text", "")
            else:
                # Handle legacy format where only chosen_path was sent
                chosen_path = choice_data
                choice_text = "Unknown choice"

            # Only process choice and update chapters for non-start messages
            if chosen_path != "start":
                # Get the chapter type from the story configuration
                story_data = load_story_data()
                story_config = story_data["story_categories"][story_category]
                current_chapter_number = len(state.chapters) + 1
                chapter_type = story_config["chapter_types"][current_chapter_number - 1]
                if not isinstance(chapter_type, ChapterType):
                    chapter_type = ChapterType(
                        chapter_type
                    )  # Convert string to enum if needed

                # Generate the new chapter content first
                chapter_content = await generate_chapter(
                    story_category, lesson_topic, state
                )

                # Create the appropriate response object based on chapter type
                if chapter_type == ChapterType.LESSON:
                    try:
                        # Sample the current question
                        current_question = sample_question(
                            lesson_topic,
                            exclude_questions=[
                                chapter.response.question["question"]
                                for chapter in state.chapters
                                if chapter.chapter_type == ChapterType.LESSON
                                and chapter.response
                            ],
                        )

                        # Create lesson response
                        response = LessonResponse(
                            question=current_question,
                            chosen_answer=choice_text,
                            is_correct=chosen_path == "correct",
                        )
                    except ValueError as e:
                        logger.error(f"Error sampling question: {e}")
                        raise
                else:
                    # Create story response
                    response = StoryResponse(
                        chosen_path=chosen_path, choice_text=choice_text
                    )

                # Create and append the new chapter with all required fields
                new_chapter = ChapterData(
                    chapter_number=current_chapter_number,
                    content=chapter_content.content,
                    chapter_type=chapter_type,
                    response=response,
                    chapter_content=chapter_content,
                )

                # Update current_chapter_id before appending new chapter
                state.current_chapter_id = chosen_path

                # Validate and append the new chapter
                try:
                    state.chapters.append(new_chapter)
                except ValueError as e:
                    logger.error(f"Error adding chapter: {e}")
                    await websocket.send_text(
                        "\n\nAn error occurred while processing your choice. Please try again."
                    )
                    continue

                # Check if we've reached the story length limit
                if len(state.chapters) >= state.story_length:
                    # Send complete state with all chapter data
                    await websocket.send_json(
                        {
                            "type": "story_complete",
                            "state": {
                                "current_chapter_id": state.current_chapter_id,
                                "chapters": [
                                    {
                                        "chapter_number": ch.chapter_number,
                                        "content": ch.content,
                                        "chapter_type": ch.chapter_type.value,
                                        "response": ch.response.dict()
                                        if ch.response
                                        else None,
                                        "chapter_content": ch.chapter_content.dict(),
                                    }
                                    for ch in state.chapters
                                ],
                                "story_length": state.story_length,
                                "stats": {
                                    "total_lessons": state.total_lessons,
                                    "correct_lesson_answers": state.correct_lesson_answers,
                                    "completion_percentage": round(
                                        (
                                            state.correct_lesson_answers
                                            / state.total_lessons
                                            * 100
                                        )
                                        if state.total_lessons > 0
                                        else 0
                                    ),
                                },
                            },
                        }
                    )
                    break

            # Generate and stream the next chapter
            try:
                chapter_content = await generate_chapter(
                    story_category, lesson_topic, state
                )
                paragraphs = [
                    p.strip()
                    for p in chapter_content.content.split("\n\n")
                    if p.strip()
                ]

                # Stream each paragraph with a delay
                for paragraph in paragraphs:
                    # Split paragraph into word batches
                    words = paragraph.split()
                    batch_size = 5
                    for i in range(0, len(words), batch_size):
                        batch = " ".join(words[i : i + batch_size])
                        await websocket.send_text(batch + " ")
                        await asyncio.sleep(WORD_DELAY)
                    await websocket.send_text("\n\n")
                    await asyncio.sleep(PARAGRAPH_DELAY)

                # Get the chapter type for the current chapter
                story_data = load_story_data()
                story_config = story_data["story_categories"][story_category]
                current_chapter_number = len(state.chapters) + 1
                chapter_type = story_config["chapter_types"][current_chapter_number - 1]
                if not isinstance(chapter_type, ChapterType):
                    chapter_type = ChapterType(chapter_type)

                # Send complete chapter data with choices
                await websocket.send_json(
                    {
                        "type": "chapter_update",
                        "state": {
                            "current_chapter_id": state.current_chapter_id,
                            "current_chapter": {
                                "chapter_number": len(state.chapters) + 1,
                                "content": chapter_content.content,
                                "chapter_type": chapter_type.value,
                                "chapter_content": chapter_content.dict(),
                            },
                        },
                    }
                )

                # Send choices separately to trigger the choice display
                await websocket.send_json(
                    {
                        "type": "choices",
                        "choices": [
                            {"text": choice.text, "id": choice.next_chapter}
                            for choice in chapter_content.choices
                        ],
                    }
                )

            except Exception as e:
                logger.error(f"Error generating chapter: {e}")
                await websocket.send_text(
                    "\n\nAn error occurred while generating the story. Please try again."
                )
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
