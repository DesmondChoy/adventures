from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket
import asyncio
import logging
import re
from app.models.story import (
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    StoryChoice,
    AdventureState,
)
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.adventure_state_manager import AdventureStateManager
from app.init_data import sample_question
import yaml

# Constants for streaming optimization
WORD_BATCH_SIZE = 5  # Number of words to send at once
WORD_DELAY = 0.02  # Reduced delay between word batches
PARAGRAPH_DELAY = 0.1  # Reduced delay between paragraphs

logger = logging.getLogger("story_app")
llm_service = LLMService()
chapter_manager = ChapterManager()


async def process_choice(
    state_manager: AdventureStateManager,
    choice_data: Dict[str, Any],
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process a user's choice and generate the next chapter.

    Args:
        state_manager: The state manager instance
        choice_data: The choice data from the client
        story_category: The story category
        lesson_topic: The lesson topic
        websocket: The WebSocket connection

    Returns:
        Tuple of (chapter_content, sampled_question, is_story_complete)
    """
    state = state_manager.get_current_state()
    if not state:
        return None, None, False

    # Extract choice information
    if isinstance(choice_data, dict):
        chosen_path = choice_data.get("chosen_path", "")
        choice_text = choice_data.get("choice_text", "")
    else:
        chosen_path = choice_data
        choice_text = "Unknown choice"

    # Handle non-start choices
    if chosen_path != "start":
        current_chapter_number = len(state.chapters) + 1
        chapter_type = state.planned_chapter_types[current_chapter_number - 1]
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
                return None, None, False
        else:
            story_response = StoryResponse(
                chosen_path=chosen_path, choice_text=choice_text
            )
            previous_chapter.response = story_response

        state.current_chapter_id = chosen_path

    # Calculate new chapter number and update story phase
    new_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[new_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Update the storytelling phase based on the new chapter number
    state.current_storytelling_phase = ChapterManager.determine_story_phase(
        new_chapter_number, state.story_length
    )

    # Generate new chapter content
    chapter_content, sampled_question = await generate_chapter(
        story_category, lesson_topic, state
    )

    # Create and append new chapter
    try:
        new_chapter = ChapterData(
            chapter_number=len(state.chapters) + 1,
            content=re.sub(
                r"^Chapter\s+\d+:\s*", "", chapter_content.content, flags=re.MULTILINE
            ).strip(),
            chapter_type=chapter_type,
            response=None,
            chapter_content=chapter_content,
            question=sampled_question,
        )
        state_manager.append_new_chapter(new_chapter)
        logger.debug(f"Added new chapter {new_chapter.chapter_number}")
        logger.debug(f"Chapter type: {chapter_type}")
        logger.debug(f"Has question: {sampled_question is not None}")
    except ValueError as e:
        logger.error(f"Error adding chapter: {e}")
        await websocket.send_text(
            "An error occurred while processing your choice. Please try again."
        )
        return None, None, False

    # Check if story is complete
    is_story_complete = len(state.chapters) >= state.story_length

    return chapter_content, sampled_question, is_story_complete


async def stream_and_send_chapter(
    websocket: WebSocket,
    chapter_content: ChapterContent,
    sampled_question: Optional[Dict[str, Any]],
    state: AdventureState,
) -> None:
    """Stream chapter content and send chapter data to the client.

    Args:
        websocket: The WebSocket connection
        chapter_content: The chapter content to stream
        sampled_question: The question data (if any)
        state: The current state
    """
    # DEBUG: Log chapter content to help diagnose chapter prefix issues
    # logger.debug(
    #     f"=== DEBUG: Chapter Content ===\n"
    #     f"Chapter Number: {state.current_chapter_number}\n"
    #     f"Raw Content:\n{chapter_content.content}\n"
    #     f"==========================="
    # )

    # Remove any "Chapter X:" prefix before streaming
    content_to_stream = re.sub(
        r"^Chapter\s+\d+:\s*", "", chapter_content.content, flags=re.MULTILINE
    ).strip()
    # Split content into paragraphs and stream
    paragraphs = [p.strip() for p in content_to_stream.split("\n\n") if p.strip()]
    for paragraph in paragraphs:
        words = paragraph.split()
        for i in range(0, len(words), WORD_BATCH_SIZE):
            batch = " ".join(words[i : i + WORD_BATCH_SIZE])
            await websocket.send_text(batch + " ")
            await asyncio.sleep(WORD_DELAY)
        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)

    # Get chapter type for current chapter
    current_chapter_number = len(state.chapters)
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Send complete chapter data
    await websocket.send_json(
        {
            "type": "chapter_update",
            "state": {
                "current_chapter_id": state.current_chapter_id,
                "current_chapter": {
                    "chapter_number": current_chapter_number,
                    "content": content_to_stream,
                    "chapter_type": chapter_type.value,
                    "chapter_content": chapter_content.content,
                    "question": sampled_question,
                },
            },
        }
    )

    # Send choices
    await websocket.send_json(
        {
            "type": "choices",
            "choices": [
                {"text": choice.text, "id": choice.next_chapter}
                for choice in chapter_content.choices
            ],
        }
    )


async def send_story_complete(
    websocket: WebSocket,
    state: AdventureState,
) -> None:
    """Send story completion data to the client.

    Args:
        websocket: The WebSocket connection
        state: The current state
    """
    # Get the final chapter (which should be CONCLUSION type)
    final_chapter = state.chapters[-1]

    # Stream the content first
    content_to_stream = final_chapter.content
    paragraphs = [p.strip() for p in content_to_stream.split("\n\n") if p.strip()]
    for paragraph in paragraphs:
        words = paragraph.split()
        for i in range(0, len(words), WORD_BATCH_SIZE):
            batch = " ".join(words[i : i + WORD_BATCH_SIZE])
            await websocket.send_text(batch + " ")
            await asyncio.sleep(WORD_DELAY)
        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)

    # Then send the completion message with stats
    await websocket.send_json(
        {
            "type": "story_complete",
            "state": {
                "current_chapter_id": state.current_chapter_id,
                "stats": {
                    "total_lessons": state.total_lessons,
                    "correct_lesson_answers": state.correct_lesson_answers,
                    "completion_percentage": round(
                        (state.correct_lesson_answers / state.total_lessons * 100)
                        if state.total_lessons > 0
                        else 0
                    ),
                },
            },
        }
    )


async def generate_chapter(
    story_category: str,
    lesson_topic: str,
    state: AdventureState,
) -> Tuple[ChapterContent, Optional[dict]]:
    """Generate a complete chapter with content and choices.

    Args:
        story_category: The story category
        lesson_topic: The lesson topic
        state: The current state

    Returns:
        Tuple of (ChapterContent, Optional[dict])
    """
    # Load story configuration
    with open("app/data/new_stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
    story_config = story_data["story_categories"][story_category]

    # Get chapter type
    current_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

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
            used_questions = [
                chapter.response.question["question"]
                for chapter in state.chapters
                if chapter.chapter_type == ChapterType.LESSON and chapter.response
            ]
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
    elif chapter_type == ChapterType.STORY:
        try:
            # First extract the choices section
            choices_match = re.search(
                r"<CHOICES>\s*(.*?)\s*</CHOICES>",
                story_content,
                re.DOTALL | re.IGNORECASE,
            )

            if not choices_match:
                logger.error(
                    "Could not find choice markers in story content. Raw content:"
                )
                logger.error(story_content)
                raise ValueError("Could not find choice markers in story content")

            # Extract choices text and clean up story content
            choices_text = choices_match.group(1).strip()
            story_content = story_content[: choices_match.start()].strip()
            # Remove any "Chapter X:" prefix, including any whitespace after it
            story_content = re.sub(
                r"^Chapter\s+\d+:\s*", "", story_content, flags=re.MULTILINE
            ).strip()

            # Initialize choices array
            choices = []

            # Try multi-line format first (within choices section)
            choice_pattern = r"Choice\s*([ABC])\s*:\s*([^\n]+)"
            matches = re.finditer(
                choice_pattern, choices_text, re.IGNORECASE | re.MULTILINE
            )
            for match in matches:
                choices.append(match.group(2).strip())

            # If no matches found, try single-line format (still within choices section)
            if not choices:
                single_line_pattern = (
                    r"Choice\s*[ABC]\s*:\s*([^.]+(?:\.\s*(?=Choice\s*[ABC]\s*:|$))?)"
                )
                matches = re.finditer(single_line_pattern, choices_text, re.IGNORECASE)
                for match in matches:
                    choices.append(match.group(1).strip())

            if not choices:
                logger.error(f"No choices found in choices text. Raw choices text:")
                logger.error(choices_text)
                raise ValueError("No choices found in story content")

            if len(choices) != 3:
                logger.warning(
                    f"Expected 3 choices but found {len(choices)}. Raw choices text:"
                )
                logger.warning(choices_text)
                # If we found at least one choice, use what we have rather than failing
                if choices:
                    logger.info("Proceeding with available choices")
                else:
                    raise ValueError("Must have at least one valid choice")

            story_choices = [
                StoryChoice(
                    text=choice_text,
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i, choice_text in enumerate(choices)
            ]
        except Exception as e:
            logger.error(f"Error parsing choices: {e}")
            story_choices = [
                StoryChoice(
                    text=f"Continue with option {i + 1}",
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i in range(3)
            ]
    else:  # CONCLUSION chapter
        story_choices = []  # No choices for conclusion chapters

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_chapter: {choice.next_chapter})")
    logger.debug("========================\n")

    return ChapterContent(content=story_content, choices=story_choices), question
