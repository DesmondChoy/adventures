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
            # logger.debug(f"Received data: {data}")

            # Extract state and choice data
            validated_state = data.get("state")
            choice_data = data.get("choice")

            # Validate required fields
            if not validated_state:
                logger.error("Missing state in message")
                await websocket.send_text("Missing state in message")
                continue

            if not choice_data:
                logger.error("Missing choice in message")
                await websocket.send_text("Missing choice in message")
                continue

            try:
                # Handle state initialization
                current_state = state_manager.get_current_state()
                if current_state is None:
                    # Initialize new state
                    total_chapters = validated_state.get(
                        "story_length", 10
                    )  # Default to 10 chapters
                    logger.debug(
                        f"Initializing state with total_chapters: {total_chapters}"
                    )
                    try:
                        state = state_manager.initialize_state(
                            total_chapters, lesson_topic, story_category
                        )
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
                    # Update existing state with validated state
                    logger.debug("Updating state from validated state")
                    logger.debug(
                        f"Validated state chapters: {len(validated_state.get('chapters', []))}"
                    )
                    if validated_state.get("chapters"):
                        last_chapter = validated_state["chapters"][-1]
                        logger.debug(
                            f"Last chapter type: {last_chapter.get('chapter_type')}"
                        )
                        logger.debug(
                            f"Last chapter has choices: {'choices' in last_chapter}"
                        )
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()
                    logger.debug(
                        f"State after update - chapters: {len(state.chapters)}"
                    )

                if state is None:
                    logger.error("State is None after initialization/update.")
                    await websocket.send_text(
                        "An error occurred. Please restart the adventure."
                    )
                    continue

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
