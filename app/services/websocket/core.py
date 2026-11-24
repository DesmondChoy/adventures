from typing import Dict, Any, Optional, Tuple, Union
from fastapi import WebSocket
import logging

from app.models.story import AdventureState, ChapterContent, ChapterType
from app.services.adventure_state_manager import AdventureStateManager

from .choice_processor import (
    process_start_choice,
    process_non_start_choice,
    handle_reveal_summary,
)

logger = logging.getLogger("story_app")


async def process_choice(
    state_manager: AdventureStateManager,
    choice_data: Union[Dict[str, Any], str],
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
    connection_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[ChapterContent], Optional[Dict[str, Any]], bool, bool]:
    """Process a user's choice and generate the next chapter.

    Args:
        state_manager: The state manager instance
        choice_data: The choice data from the client (can be a dictionary or a string)
        story_category: The story category
        lesson_topic: The lesson topic
        websocket: The WebSocket connection
        connection_data: Optional connection-specific data including adventure_id

    Returns:
        Tuple of (chapter_content, sampled_question, is_story_complete, already_streamed)
    """
    state = state_manager.get_current_state()
    if not state:
        return None, None, False, False

    logger.debug(f"Raw choice_data: {choice_data}")
    if isinstance(choice_data, dict):
        chosen_path = (
            choice_data.get("id")
            or choice_data.get("chosen_path")
            or choice_data.get("choice", "")
        )
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

    if chosen_path == "reveal_summary":
        return await handle_reveal_summary(
            state, state_manager, websocket, connection_data
        )

    if chosen_path != "start":
        return await process_non_start_choice(
            chosen_path,
            choice_text,
            state,
            state_manager,
            story_category,
            lesson_topic,
            websocket,
            connection_data,
        )

    return await process_start_choice(
        state, state_manager, story_category, lesson_topic, websocket, connection_data
    )



async def send_story_complete(
    websocket: WebSocket,
    state: AdventureState,
    connection_data: Optional[Dict[str, Any]] = None,
    already_streamed: bool = False,
    story_category: Optional[str] = None,
    lesson_topic: Optional[str] = None,
    is_resumption: bool = False,
) -> None:
    """Send story completion data to the client.

    Args:
        websocket: The WebSocket connection
        state: The current state
        connection_data: Optional connection-specific data including adventure_id
        already_streamed: If True, skip streaming content as it was already live-streamed
        story_category: Story category used for telemetry metadata.
        lesson_topic: Lesson topic used for telemetry metadata.
        is_resumption: Whether the conclusion is being replayed after a resume.
    """
    from .image_generator import process_image_tasks, start_image_generation_tasks
    from .stream_handler import _record_chapter_viewed, stream_conclusion_content

    if not state.chapters:
        logger.error("send_story_complete called with empty chapters list")
        await websocket.send_json(
            {
                "type": "error",
                "message": "Story completion data unavailable. Please refresh and try again.",
            }
        )
        return

    final_chapter = state.chapters[-1]
    if final_chapter.chapter_type != ChapterType.CONCLUSION:
        logger.error(
            "send_story_complete called before CONCLUSION chapter",
            extra={
                "chapter_number": final_chapter.chapter_number,
                "chapter_type": final_chapter.chapter_type.value,
            },
        )
        await websocket.send_json(
            {
                "type": "error",
                "message": "Story completion data unavailable. Please refresh and try again.",
            }
        )
        return

    await websocket.send_json({
        "type": "chapter_update",
        "current_chapter": final_chapter.chapter_number,
        "total_chapters": state.story_length
    })

    if not already_streamed:
        await stream_conclusion_content(final_chapter.content, websocket)

    await _record_chapter_viewed(
        state=state,
        chapter_number=final_chapter.chapter_number,
        chapter_type=final_chapter.chapter_type,
        adventure_id=(
            connection_data.get("adventure_id") if connection_data else None
        ),
        story_category=story_category,
        lesson_topic=lesson_topic,
        connection_data=connection_data,
        is_resumption=is_resumption,
    )

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
                "show_summary_button": True,
                "chapter_summaries": state.chapter_summaries,
            },
        }
    )
    logger.info("Sent story_complete message - Memory Lane button now visible")

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

        if image_tasks:
            await process_image_tasks(image_tasks, final_chapter.chapter_number, websocket)
            logger.info("Processed image tasks for CONCLUSION chapter")
    except Exception as e:
        logger.error(f"Error with image generation for CONCLUSION: {str(e)}")
