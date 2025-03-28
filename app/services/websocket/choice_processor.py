from typing import Dict, Any, Optional, Tuple, List
from fastapi import WebSocket
import logging
import re

from app.models.story import (
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    AdventureState,
)
from app.services.adventure_state_manager import AdventureStateManager
from app.services.chapter_manager import ChapterManager
from app.services.state_storage_service import StateStorageService

from .content_generator import generate_chapter
from .summary_generator import generate_summary_content, stream_summary_content

logger = logging.getLogger("story_app")
chapter_manager = ChapterManager()
state_storage_service = StateStorageService()


async def handle_reveal_summary(
    state: AdventureState, state_manager: AdventureStateManager, websocket: WebSocket
) -> Tuple[None, None, bool]:
    """Handle the reveal_summary special choice."""
    logger.info("Processing reveal_summary choice")
    logger.info(f"Current state has {len(state.chapters)} chapters")
    logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")

    # Get the CONCLUSION chapter
    if state.chapters and state.chapters[-1].chapter_type == ChapterType.CONCLUSION:
        conclusion_chapter = state.chapters[-1]
        logger.info(f"Found CONCLUSION chapter: {conclusion_chapter.chapter_number}")
        logger.info(
            f"CONCLUSION chapter content length: {len(conclusion_chapter.content)}"
        )

        # Process it like a regular choice with placeholder values
        story_response = StoryResponse(chosen_path="reveal_summary", choice_text=" ")
        conclusion_chapter.response = story_response
        logger.info(
            "Created placeholder response for CONCLUSION chapter with whitespace"
        )

        await generate_conclusion_chapter_summary(conclusion_chapter, state, websocket)

    # Create and generate the SUMMARY chapter
    summary_chapter = chapter_manager.create_summary_chapter(state)
    summary_content = await generate_summary_content(state)
    summary_chapter.content = summary_content
    summary_chapter.chapter_content.content = summary_content

    # Add the SUMMARY chapter to the state
    state_manager.append_new_chapter(summary_chapter)

    await stream_summary_content(summary_content, websocket)

    # Send the complete summary data
    await websocket.send_json(
        {
            "type": "summary_complete",
            "state": {
                "current_chapter_id": state.current_chapter_id,
                "current_chapter": {
                    "chapter_number": summary_chapter.chapter_number,
                    "content": summary_content,
                    "chapter_type": ChapterType.SUMMARY.value,
                },
                "stats": {
                    "total_lessons": state.total_lessons,
                    "correct_lesson_answers": state.correct_lesson_answers,
                    "completion_percentage": round(
                        (state.correct_lesson_answers / state.total_lessons * 100)
                        if state.total_lessons > 0
                        else 0
                    ),
                },
                "chapter_summaries": state.chapter_summaries,
            },
        }
    )

    return None, None, False


async def generate_conclusion_chapter_summary(
    conclusion_chapter: ChapterData, state: AdventureState, websocket: WebSocket
) -> None:
    """Generate and store summary for the conclusion chapter."""
    try:
        logger.info(f"Generating summary for CONCLUSION chapter")
        summary_result = await chapter_manager.generate_chapter_summary(
            conclusion_chapter.content,
            " ",  # Whitespace for chosen_choice
            " ",  # Whitespace for choice_context
        )

        # Extract title and summary from the result
        title = summary_result.get("title", "Chapter Summary")
        summary_text = summary_result.get("summary", "Summary not available")

        logger.info(f"Generated CONCLUSION chapter summary: {summary_text[:100]}...")

        # Store the summary
        if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
            logger.info(
                f"Adding placeholder summaries up to chapter {conclusion_chapter.chapter_number - 1}"
            )
            while len(state.chapter_summaries) < conclusion_chapter.chapter_number - 1:
                state.chapter_summaries.append("Chapter summary not available")
                # Also add placeholder titles
                if hasattr(state, "summary_chapter_titles"):
                    state.summary_chapter_titles.append(
                        f"Chapter {len(state.summary_chapter_titles) + 1}"
                    )

            # Add the new summary and title
            state.chapter_summaries.append(summary_text)
            # Add the title if the field exists
            if hasattr(state, "summary_chapter_titles"):
                state.summary_chapter_titles.append(title)
        else:
            logger.info(
                f"Updating existing summary at index {conclusion_chapter.chapter_number - 1}"
            )
            state.chapter_summaries[conclusion_chapter.chapter_number - 1] = (
                summary_text
            )
            # Update the title if the field exists
            if hasattr(state, "summary_chapter_titles"):
                # Ensure the list is long enough
                while (
                    len(state.summary_chapter_titles)
                    < conclusion_chapter.chapter_number
                ):
                    state.summary_chapter_titles.append(
                        f"Chapter {len(state.summary_chapter_titles) + 1}"
                    )
                state.summary_chapter_titles[conclusion_chapter.chapter_number - 1] = (
                    title
                )

        logger.info(
            f"Stored summary for chapter {conclusion_chapter.chapter_number}: {summary_text}"
        )
        if hasattr(state, "summary_chapter_titles"):
            logger.info(
                f"Stored title for chapter {conclusion_chapter.chapter_number}: {title}"
            )

        # Store the updated state in StateStorageService
        state_id = await state_storage_service.store_state(state.dict())
        logger.info(
            f"Stored state with ID: {state_id} after generating CONCLUSION chapter summary"
        )

        # Include the state_id in the response to the client
        await websocket.send_json({"type": "summary_ready", "state_id": state_id})
    except Exception as e:
        logger.error(f"Error generating chapter summary: {str(e)}", exc_info=True)
        if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
            logger.warning(
                f"Using fallback summary for chapter {conclusion_chapter.chapter_number}"
            )
            state.chapter_summaries.append("Chapter summary not available")


async def process_non_start_choice(
    chosen_path: str,
    choice_text: str,
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process a non-start choice from the user."""
    logger.debug(f"Processing non-start choice: {chosen_path}")
    logger.debug(f"Current state chapters: {len(state.chapters)}")

    current_chapter_number = len(state.chapters) + 1
    logger.debug(f"Processing chapter {current_chapter_number}")
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)
    logger.debug(f"Next chapter type: {chapter_type}")

    previous_chapter = state.chapters[-1]
    logger.debug("\n=== DEBUG: Previous Chapter Info ===")
    logger.debug(f"Previous chapter number: {previous_chapter.chapter_number}")
    logger.debug(f"Previous chapter type: {previous_chapter.chapter_type}")
    logger.debug(
        f"Previous chapter has response: {previous_chapter.response is not None}"
    )
    if previous_chapter.response:
        logger.debug(
            f"Previous chapter response type: {type(previous_chapter.response)}"
        )
    logger.debug("===================================\n")

    if previous_chapter.chapter_type == ChapterType.LESSON:
        await process_lesson_response(previous_chapter, choice_text, state, websocket)
    else:
        await process_story_response(previous_chapter, chosen_path, choice_text, state)

    # Generate a chapter summary for the previous chapter
    await generate_chapter_summary(previous_chapter, state)

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
    new_chapter = await create_and_append_chapter(
        chapter_content, chapter_type, sampled_question, state_manager, websocket
    )
    if not new_chapter:
        return None, None, False

    # Check if story is complete - when we've reached the story length
    is_story_complete = len(state.chapters) == state.story_length

    return chapter_content, sampled_question, is_story_complete


async def process_start_choice(
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process the start choice (first chapter)."""
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

    # No need to process previous chapter for start choice
    is_story_complete = False

    return chapter_content, sampled_question, is_story_complete


async def process_lesson_response(
    previous_chapter: ChapterData,
    choice_text: str,
    state: AdventureState,
    websocket: WebSocket,
) -> None:
    """Process a response to a lesson chapter."""
    logger.debug("\n=== DEBUG: Processing Lesson Response ===")
    logger.debug(f"Previous chapter number: {previous_chapter.chapter_number}")
    logger.debug(
        f"Previous chapter has question: {previous_chapter.question is not None}"
    )

    try:
        # Create lesson response using the stored question data
        if previous_chapter.question:
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

            # Store in lesson_questions array for summary chapter
            if not hasattr(state, "lesson_questions"):
                state.lesson_questions = []

            # Create question object for summary display
            question_obj = {
                "question": previous_chapter.question.get(
                    "question", "Unknown question"
                ),
                "answers": previous_chapter.question.get("answers", []),
                "chosen_answer": choice_text,
                "is_correct": choice_text == correct_answer,
                "explanation": previous_chapter.question.get("explanation", ""),
                "correct_answer": correct_answer,
            }

            # Append to state's lesson_questions
            state.lesson_questions.append(question_obj)
            logger.info(
                f"Added question to lesson_questions array: {question_obj['question']}"
            )

            logger.debug("\n=== DEBUG: Created Lesson Response ===")
            logger.debug(f"Question: {previous_chapter.question['question']}")
            logger.debug(f"Chosen answer: {choice_text}")
            logger.debug(f"Correct answer: {correct_answer}")
            logger.debug(f"Is correct: {choice_text == correct_answer}")
            logger.debug(
                f"Questions in lesson_questions: {len(state.lesson_questions)}"
            )
            logger.debug("====================================\n")
        else:
            logger.error("Previous chapter missing question data")
            await websocket.send_text(
                "An error occurred while processing your answer. Missing question data."
            )
            raise ValueError("Missing question data in chapter")
    except Exception as e:
        logger.error(f"Error creating lesson response: {e}")
        await websocket.send_text(
            "An error occurred while processing your answer. Please try again."
        )
        raise ValueError(f"Error processing lesson response: {str(e)}")


async def process_story_response(
    previous_chapter: ChapterData,
    chosen_path: str,
    choice_text: str,
    state: AdventureState,
) -> None:
    """Process a response to a story chapter."""
    story_response = StoryResponse(chosen_path=chosen_path, choice_text=choice_text)
    previous_chapter.response = story_response
    logger.debug(f"Created story response: {story_response}")

    # Handle first chapter agency choice
    if (
        previous_chapter.chapter_number == 1
        and previous_chapter.chapter_type == ChapterType.STORY
    ):
        logger.debug("Processing first chapter agency choice")

        # Extract agency category and visual details
        agency_category = ""
        visual_details = ""

        # Try to find the matching agency option
        try:
            from app.services.llm.prompt_templates import categories

            for category_name, category_options in categories.items():
                for option in category_options:
                    # Extract the name part (before the bracket)
                    option_name = option.split("[")[0].strip()
                    # Check if this option matches the choice text
                    if (
                        option_name.lower() in choice_text.lower()
                        or choice_text.lower() in option_name.lower()
                    ):
                        agency_category = category_name
                        # Extract visual details from square brackets
                        match = re.search(r"\[(.*?)\]", option)
                        if match:
                            visual_details = match.group(1)
                        break
                if visual_details:
                    break
        except Exception as e:
            logger.error(f"Error extracting agency details: {e}")

        # Store agency choice in metadata with visual details
        state.metadata["agency"] = {
            "type": "choice",
            "name": "from Chapter 1",
            "description": choice_text,
            "category": agency_category,
            "visual_details": visual_details,
            "properties": {"strength": 1},
            "growth_history": [],
            "references": [],
        }

        logger.debug(f"Stored agency choice from Chapter 1: {choice_text}")
        logger.debug(f"Agency category: {agency_category}")
        logger.debug(f"Visual details: {visual_details}")


async def generate_chapter_summary(
    previous_chapter: ChapterData, state: AdventureState
) -> None:
    """Generate a summary for the previous chapter."""
    try:
        logger.info(f"Generating summary for chapter {previous_chapter.chapter_number}")

        # Extract the choice text and context from the response
        choice_text = ""
        choice_context = ""

        if isinstance(previous_chapter.response, StoryResponse):
            choice_text = previous_chapter.response.choice_text
            # No additional context needed for STORY chapters
        elif isinstance(previous_chapter.response, LessonResponse):
            choice_text = previous_chapter.response.chosen_answer
            choice_context = (
                " (Correct answer)"
                if previous_chapter.response.is_correct
                else " (Incorrect answer)"
            )

        summary_result = await chapter_manager.generate_chapter_summary(
            previous_chapter.content, choice_text, choice_context
        )

        # Extract title and summary from the result
        title = summary_result.get("title", "Chapter Summary")
        summary_text = summary_result.get("summary", "Summary not available")

        await store_chapter_summary(previous_chapter, state, title, summary_text)
    except Exception as e:
        logger.error(f"Error generating chapter summary: {str(e)}")
        # Don't fail the whole process if summary generation fails
        if len(state.chapter_summaries) < previous_chapter.chapter_number:
            state.chapter_summaries.append("Chapter summary not available")


async def store_chapter_summary(
    chapter: ChapterData, state: AdventureState, title: str, summary_text: str
) -> None:
    """Store chapter summary and title in the state."""
    if len(state.chapter_summaries) < chapter.chapter_number:
        # If this is the first summary, we might need to add placeholders for previous chapters
        while len(state.chapter_summaries) < chapter.chapter_number - 1:
            state.chapter_summaries.append("Chapter summary not available")
            # Also add placeholder titles
            if hasattr(state, "summary_chapter_titles"):
                state.summary_chapter_titles.append(
                    f"Chapter {len(state.summary_chapter_titles) + 1}"
                )

        # Add the new summary and title
        state.chapter_summaries.append(summary_text)
        # Add the title if the field exists
        if hasattr(state, "summary_chapter_titles"):
            state.summary_chapter_titles.append(title)
    else:
        # Replace the summary at the correct index
        state.chapter_summaries[chapter.chapter_number - 1] = summary_text
        # Replace the title if the field exists
        if hasattr(state, "summary_chapter_titles"):
            # Ensure the list is long enough
            while len(state.summary_chapter_titles) < chapter.chapter_number:
                state.summary_chapter_titles.append(
                    f"Chapter {len(state.summary_chapter_titles) + 1}"
                )
            state.summary_chapter_titles[chapter.chapter_number - 1] = title

    logger.info(f"Stored summary for chapter {chapter.chapter_number}: {summary_text}")
    if hasattr(state, "summary_chapter_titles"):
        logger.info(f"Stored title for chapter {chapter.chapter_number}: {title}")


async def create_and_append_chapter(
    chapter_content: ChapterContent,
    chapter_type: ChapterType,
    sampled_question: Optional[Dict[str, Any]],
    state_manager: AdventureStateManager,
    websocket: WebSocket,
) -> Optional[ChapterData]:
    """Create and append a new chapter to the state."""
    from .content_generator import clean_chapter_content

    try:
        # Use the Pydantic validator to clean the content
        validated_content = clean_chapter_content(chapter_content.content)

        new_chapter = ChapterData(
            chapter_number=len(state_manager.get_current_state().chapters) + 1,
            content=validated_content.strip(),
            chapter_type=chapter_type,
            response=None,
            chapter_content=chapter_content,
            question=sampled_question,
        )
        state_manager.append_new_chapter(new_chapter)
        logger.debug(f"Added new chapter {new_chapter.chapter_number}")
        logger.debug(f"Chapter type: {chapter_type}")
        logger.debug(f"Has question: {sampled_question is not None}")
        return new_chapter
    except ValueError as e:
        logger.error(f"Error adding chapter: {e}")
        await websocket.send_text(
            "An error occurred while processing your choice. Please try again."
        )
        return None
