from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.services.adventure_state_manager import AdventureStateManager
from app.services.websocket_service import (
    process_choice,
    stream_and_send_chapter,
    send_story_complete,
)

router = APIRouter()
logger = logging.getLogger("story_app")


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}"
    )

    state_manager = AdventureStateManager()

    try:
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
                        # Initialize state with story category
                        state_manager.initialize_state(
                            total_chapters, lesson_topic, story_category
                        )
                        state = state_manager.get_current_state()

                        logger.info(
                            "Initialized adventure state",
                            extra={
                                "story_category": story_category,
                                "lesson_topic": lesson_topic,
                                "total_chapters": total_chapters,
                            },
                        )

                    except ValueError as e:
                        error_message = f"Error initializing state: {e}"
                        logger.error(error_message)
                        await websocket.send_text(error_message)
                        await websocket.close(code=1001)
                        return  # Exit to prevent further processing
                else:
                    logger.debug("Updating existing state from client.")
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()

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

            try:
                # Process the choice and generate next chapter
                (
                    chapter_content,
                    sampled_question,
                    is_story_complete,
                ) = await process_choice(
                    state_manager=state_manager,
                    choice_data=choice_data,
                    story_category=story_category,
                    lesson_topic=lesson_topic,
                    websocket=websocket,
                )

                if chapter_content is None:
                    continue

                # If story is complete, send completion data and end
                if is_story_complete:
                    await send_story_complete(
                        websocket=websocket,
                        state=state_manager.get_current_state(),
                    )
                    break

                # Stream chapter content and send updates
                await stream_and_send_chapter(
                    websocket=websocket,
                    chapter_content=chapter_content,
                    sampled_question=sampled_question,
                    state=state_manager.get_current_state(),
                )

            except Exception as e:
                logger.error(f"Error generating chapter: {e}")
                await websocket.send_text(
                    "\n\nAn error occurred while generating the story. Please try again."
                )
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
