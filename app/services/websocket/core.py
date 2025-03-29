from typing import Dict, Any, Optional, Tuple
from fastapi import WebSocket
import logging

from app.models.story import ChapterContent, AdventureState
from app.services.adventure_state_manager import AdventureStateManager

from .choice_processor import (
    process_start_choice,
    process_non_start_choice,
    handle_reveal_summary,
)
from .stream_handler import stream_chapter_content

logger = logging.getLogger("story_app")


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

    # Extract choice information and debug state
    logger.debug(f"Raw choice_data: {choice_data}")
    if isinstance(choice_data, dict):
        chosen_path = choice_data.get("id") or choice_data.get("chosen_path", "")
        choice_text = choice_data.get("text") or choice_data.get("choice_text", "")
        if "state" in choice_data:
            logger.debug("Choice data contains state")
            logger.debug(
                f"State chapters: {len(choice_data['state'].get('chapters', []))}"
            )
            if choice_data["state"].get("chapters"):
                last_chapter = choice_data["state"]["chapters"][-1]
                logger.debug(f"Last chapter type: {last_chapter.get('chapter_type')}")
                logger.debug(f"Last chapter has choices: {'choices' in last_chapter}")
    else:
        chosen_path = str(choice_data)
        choice_text = "Unknown choice"
        logger.debug("Choice data is not a dictionary")

    # Check for special "reveal_summary" choice
    if chosen_path == "reveal_summary":
        return await handle_reveal_summary(state, state_manager, websocket)

    # Handle non-start choices
    if chosen_path != "start":
        return await process_non_start_choice(
            chosen_path,
            choice_text,
            state,
            state_manager,
            story_category,
            lesson_topic,
            websocket,
        )

    # Handle start choice (initialize new story)
    return await process_start_choice(
        state, state_manager, story_category, lesson_topic
    )


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
    await stream_chapter_content(websocket, chapter_content, sampled_question, state)


async def send_story_complete(
    websocket: WebSocket,
    state: AdventureState,
) -> None:
    """Send story completion data to the client.

    Args:
        websocket: The WebSocket connection
        state: The current state
    """
    from .stream_handler import stream_conclusion_content
    from .image_generator import start_image_generation_tasks, process_image_tasks

    # Get the final chapter (which should be CONCLUSION type)
    final_chapter = state.chapters[-1]

    # Start image generation for the CONCLUSION chapter
    try:
        image_tasks = await start_image_generation_tasks(
            final_chapter.chapter_number,
            final_chapter.chapter_type,
            final_chapter.chapter_content,
            state,
        )
        logger.info(
            f"Started {len(image_tasks)} image generation tasks for CONCLUSION chapter"
        )
    except Exception as e:
        logger.error(f"Error starting image generation tasks for CONCLUSION: {str(e)}")
        image_tasks = []  # Empty list as fallback

    # Stream the content first
    await stream_conclusion_content(final_chapter.content, websocket)

    # Then send the completion message with stats and a button to view the summary
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
                "show_summary_button": True,  # Signal to show the summary button
                # Include chapter_summaries in the response for simulation logging
                "chapter_summaries": state.chapter_summaries,
            },
        }
    )

    # Process image tasks after sending the completion message
    if image_tasks:
        await process_image_tasks(image_tasks, final_chapter.chapter_number, websocket)
        logger.info(f"Processed image tasks for CONCLUSION chapter")
    else:
        logger.warning(f"No image tasks available for CONCLUSION chapter")
