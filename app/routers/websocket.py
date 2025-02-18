from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.story import (
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    StoryChoice,
)
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.adventure_state_manager import AdventureStateManager
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
chapter_manager = ChapterManager()  # Keep ChapterManager for chapter generation
state_manager = AdventureStateManager()  # Instantiate AdventureStateManager
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


async def generate_chapter(
    story_category: str,
    lesson_topic: str,
    state,  # Keep state parameter for now
) -> tuple[ChapterContent, dict | None]:
    """Generate a complete chapter with content and choices."""
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Get the chapter type from the planned chapter types in state
    current_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
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
        async for chunk in llm_service.generate_chapter_stream(
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

            # Remove any "Chapter X:" prefix
            story_content = re.sub(r"^Chapter \d+:\s*", "", story_content).strip()

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

    # Return both the chapter content and the question (if it's a lesson chapter)
    return ChapterContent(content=story_content, choices=story_choices), question


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}"
    )

    state_manager = AdventureStateManager()  # Instantiate AdventureStateManager

    try:
        state_manager = AdventureStateManager()  # Instantiate AdventureStateManager
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received data: {data}")

            if "state" in data:
                validated_state = data["state"]
                if state_manager.get_current_state() is None:
                    total_chapters = validated_state["story_length"]
                    logger.debug(
                        f"Initializing state with total_chapters: {total_chapters}"
                    )
                    try:
                        state_manager.initialize_state(total_chapters, lesson_topic)
                        state = state_manager.get_current_state()  # Get the state

                        logger.debug("=== Story Configuration ===")
                        logger.debug(f"Category: {story_category}")
                        logger.debug(f"Topic: {lesson_topic}")
                        logger.debug(f"Length: {total_chapters} chapters")
                        logger.debug("=============================")

                    except ValueError as e:
                        logger.error(f"Error initializing state: {e}")
                        await websocket.send_text(str(e))
                        break
                else:
                    logger.debug("Updating existing state from client.")
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()  # Get the state

            if (
                state is None
            ):  # Check if state is still None after initialization/update
                logger.error("State is None after initialization/update.")
                await websocket.send_text(
                    "An error occurred. Please restart the adventure."
                )
                continue

            choice_data = data.get("choice")
            if choice_data is None:
                continue

            if isinstance(choice_data, dict):
                chosen_path = choice_data.get("chosen_path", "")
                choice_text = choice_data.get("choice_text", "")
            else:
                chosen_path = choice_data
                choice_text = "Unknown choice"

            try:
                if chosen_path != "start":
                    current_chapter_number = len(state.chapters) + 1
                    chapter_type = state.planned_chapter_types[
                        current_chapter_number - 1
                    ]
                    if not isinstance(chapter_type, ChapterType):
                        chapter_type = ChapterType(chapter_type)

                    previous_chapter = state.chapters[-1]
                    if previous_chapter.chapter_type == ChapterType.LESSON:
                        try:
                            correct_answer = next(
                                answer["text"]
                                for answer in previous_chapter.question["answers"]
                                if answer["is_correct"]
                            )
                            lesson_response = LessonResponse(
                                question=previous_chapter.question,
                                chosen_answer=choice_text,
                                is_correct=choice_text == correct_answer,
                            )
                            previous_chapter.response = lesson_response
                            logger.debug(f"Created lesson response: {lesson_response}")
                        except Exception as e:
                            logger.error(f"Error creating lesson response: {e}")
                            await websocket.send_text(
                                "An error occurred while processing your answer. Please try again."
                            )
                            continue
                    else:
                        story_response = StoryResponse(
                            chosen_path=chosen_path, choice_text=choice_text
                        )
                        previous_chapter.response = story_response

                    state.current_chapter_id = chosen_path

                    chapter_content, sampled_question = await generate_chapter(
                        story_category, lesson_topic, state
                    )

                    try:
                        new_chapter = ChapterData(
                            chapter_number=current_chapter_number,
                            content=chapter_content.content,
                            chapter_type=chapter_type,
                            response=None,
                            chapter_content=chapter_content,
                            question=sampled_question,
                        )
                        state_manager.append_new_chapter(new_chapter)
                        state = state_manager.get_current_state()  # Get updated state
                        logger.debug(f"Added new chapter {current_chapter_number}")
                        logger.debug(f"Chapter type: {chapter_type}")
                        logger.debug(f"Has question: {sampled_question is not None}")
                    except ValueError as e:
                        logger.error(f"Error adding chapter: {e}")
                        await websocket.send_text(
                            "An error occurred while processing your choice. Please try again."
                        )
                        continue

                    if len(state.chapters) >= state.story_length:
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
                                            "chapter_content": ch.chapter_content.dict()
                                            if ch.chapter_content
                                            else None,
                                            "question": ch.question,
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

                if chosen_path == "start":
                    chapter_content, sampled_question = await generate_chapter(
                        story_category, lesson_topic, state
                    )

                    chapter_type = state.planned_chapter_types[0]

                    new_chapter = ChapterData(
                        chapter_number=1,
                        content=chapter_content.content,
                        chapter_type=chapter_type,
                        chapter_content=chapter_content,
                        response=None,
                        question=sampled_question,
                    )
                    state_manager.append_new_chapter(new_chapter)  # Use state manager
                    state = state_manager.get_current_state()  # Get the updated state

                paragraphs = [
                    p.strip()
                    for p in chapter_content.content.split("\n\n")
                    if p.strip()
                ]

                # Stream each paragraph with a delay
                for paragraph in paragraphs:
                    # Split paragraph into word batches
                    words = paragraph.split()
                    for i in range(0, len(words), WORD_BATCH_SIZE):
                        batch = " ".join(words[i : i + WORD_BATCH_SIZE])
                        await websocket.send_text(batch + " ")
                        await asyncio.sleep(WORD_DELAY)
                    await websocket.send_text("\n\n")
                    await asyncio.sleep(PARAGRAPH_DELAY)

                # Get the chapter type for the current chapter
                current_chapter_number = len(state.chapters) + 1
                chapter_type = state.planned_chapter_types[current_chapter_number - 1]
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
                                "question": sampled_question,  # Include question in chapter update
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
