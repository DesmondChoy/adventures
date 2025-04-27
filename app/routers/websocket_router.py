from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.services.adventure_state_manager import AdventureStateManager
from app.services.state_storage_service import StateStorageService
from app.services.websocket_service import (
    process_choice,
    stream_and_send_chapter,
    send_story_complete,
)

router = APIRouter()
logger = logging.getLogger("story_app")


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(
    websocket: WebSocket,
    story_category: str,
    lesson_topic: str,
    client_uuid: str = None,
    difficulty: str = None,
):
    """Handle WebSocket connection for story streaming.

    Args:
        websocket: The WebSocket connection
        story_category: The story category to use
        lesson_topic: The topic of the lessons
        client_uuid: Client UUID for identifying returning users
        difficulty: Optional difficulty level for lessons ("Reasonably Challenging" or "Very Challenging")
    """
    await websocket.accept()
    # --- ADDED LOGGING ---
    logger.info(f"WebSocket attempting connection with client_uuid: {client_uuid}")
    # --- END ADDED LOGGING ---
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}, client_uuid: {client_uuid}, difficulty: {difficulty}"
    )

    # TODO: Implement difficulty toggle in UI to allow users to select difficulty level

    state_manager = AdventureStateManager()
    state_storage_service = StateStorageService()

    # Store connection-specific data
    connection_data = {
        "adventure_id": None,  # Will be set when we create or load an adventure
        "client_uuid": client_uuid,
    }

    try:
        # Check for existing active adventure if client_uuid is provided
        if client_uuid:
            try:
                # Look for an active (incomplete) adventure for this client
                active_adventure_id = (
                    await state_storage_service.get_active_adventure_id(client_uuid)
                )

                if active_adventure_id:
                    logger.info(
                        f"Found active adventure {active_adventure_id} for client {client_uuid}"
                    )

                    # Store the adventure_id in connection data
                    connection_data["adventure_id"] = active_adventure_id

                    # Send a message to the client that we found an existing adventure
                    await websocket.send_json(
                        {
                            "type": "adventure_status",
                            "status": "existing",
                            "adventure_id": active_adventure_id,
                        }
                    )
                else:
                    logger.info(f"No active adventure found for client {client_uuid}")

                    # Send a message to the client that we'll create a new adventure
                    await websocket.send_json(
                        {"type": "adventure_status", "status": "new"}
                    )
            except Exception as e:
                logger.error(f"Error checking for active adventure: {e}")
                # Continue with normal flow - we'll create a new adventure

        # --- Load state immediately if an active adventure was found ---
        loaded_state_from_storage = None
        if connection_data["adventure_id"]:
            try:
                stored_state = await state_storage_service.get_state(
                    connection_data["adventure_id"]
                )
                if stored_state:
                    logger.info(
                        f"Attempting to reconstruct state from storage for ID: {connection_data['adventure_id']}"
                    )
                    # Reconstruct the state immediately using the state_manager instance
                    loaded_state_from_storage = (
                        await state_manager.reconstruct_state_from_storage(stored_state)
                    )
                    if loaded_state_from_storage:
                        logger.info(
                            "Successfully reconstructed and set state from storage upon connection."
                        )
                        # Send confirmation to client
                        await websocket.send_json(
                            {
                                "type": "adventure_loaded",
                                "adventure_id": connection_data["adventure_id"],
                                "current_chapter": loaded_state_from_storage.current_chapter_number,
                                "total_chapters": loaded_state_from_storage.story_length,
                            }
                        )
                        # Send the current chapter of the loaded state immediately
                        # NOTE: stream_and_send_chapter needs modification to handle sending only current chapter without generating new one
                        # For now, we might just send a confirmation and let the client request normally?
                        # Or modify stream_and_send_chapter later. Let's just log for now.
                        logger.info(
                            f"Loaded state indicates current chapter is {loaded_state_from_storage.current_chapter_number}"
                        )
                        # TODO: Decide how to send the current chapter content upon resume.
                        # await stream_and_send_chapter(
                        #     websocket=websocket,
                        #     chapter_content=None,
                        #     sampled_question=None,
                        #     state=loaded_state_from_storage,
                        #     # send_only_current_chapter=True # This flag needs to be implemented in the service
                        # )
                    else:
                        logger.error(
                            f"Failed to reconstruct state from storage for ID: {connection_data['adventure_id']}. Will create new adventure."
                        )
                        connection_data["adventure_id"] = None  # Clear invalid ID
                else:
                    logger.warning(
                        f"No state found in storage for supposedly active ID: {connection_data['adventure_id']}. Will create new adventure."
                    )
                    connection_data["adventure_id"] = None  # Clear invalid ID
            except Exception as e:
                logger.error(f"Error loading state from storage upon connection: {e}")
                connection_data["adventure_id"] = None  # Clear invalid ID
        # --- End of immediate state loading ---

        while True:
            data = await websocket.receive_json()
            # logger.debug(f"Received data: {data}")

            # Extract message type, state and choice data
            message_type = data.get("type", "process_choice")
            validated_state = data.get("state")
            choice_data = data.get("choice")

            # Debug logging for incoming data
            logger.debug("\n=== DEBUG: WebSocket Message ===")
            logger.debug(f"Has state: {validated_state is not None}")
            if validated_state:
                logger.debug(
                    f"State chapters: {len(validated_state.get('chapters', []))}"
                )
                if validated_state.get("chapters"):
                    last_chapter = validated_state["chapters"][-1]
                    logger.debug(
                        f"Last chapter type: {last_chapter.get('chapter_type')}"
                    )
                    logger.debug(
                        f"Last chapter has response: {'response' in last_chapter}"
                    )
                    if "response" in last_chapter:
                        logger.debug(f"Response data: {last_chapter['response']}")

            logger.debug(f"Has choice: {choice_data is not None}")
            if choice_data:
                logger.debug(f"Choice data: {choice_data}")
            logger.debug("==============================\n")

            # All message types are now handled through process_choice
            # The special "reveal_summary" choice is handled in process_choice

            # For regular choice processing, validate required fields
            if not validated_state:
                logger.error("Missing state in message")
                await websocket.send_text("Missing state in message")
                continue

            if not choice_data:
                logger.error("Missing choice in message")
                await websocket.send_text("Missing choice in message")
                continue

            try:
                # --- State Handling within loop ---
                # Get the state (might have been loaded on connection, or needs init)
                current_state = state_manager.get_current_state()

                # If state is still None (wasn't loaded on connect and not init yet), initialize it
                if current_state is None:
                    # This should only happen for BRAND NEW adventures now
                    if connection_data["adventure_id"]:
                        logger.warning(
                            f"State is None but adventure_id {connection_data['adventure_id']} exists. Re-initializing."
                        )
                        connection_data["adventure_id"] = None  # Force re-creation

                    # Initialize new state
                    total_chapters = validated_state.get(
                        "story_length", 10
                    )  # Default to 10 chapters
                    logger.debug(
                        f"Initializing state with total_chapters: {total_chapters}"
                    )
                    try:
                        state = state_manager.initialize_state(
                            total_chapters, lesson_topic, story_category, difficulty
                        )

                        # Ensure client_uuid is stored in metadata if provided
                        if client_uuid and state.metadata is not None:
                            state.metadata["client_uuid"] = client_uuid

                        logger.info(
                            "Initialized adventure state",
                            extra={
                                "story_category": story_category,
                                "lesson_topic": lesson_topic,
                                "total_chapters": total_chapters,
                                "difficulty": difficulty,
                                "client_uuid": client_uuid,
                            },
                        )

                        # Store the new state immediately to get an adventure_id
                        try:
                            adventure_id = await state_storage_service.store_state(
                                state.dict(),
                                user_id=None,  # No authenticated user yet
                                lesson_topic=lesson_topic,  # Pass lesson topic directly
                            )

                            # Store the adventure_id in connection data
                            connection_data["adventure_id"] = adventure_id
                            logger.info(f"Stored new state with ID: {adventure_id}")

                            # Send a message to the client with the adventure_id
                            await websocket.send_json(
                                {
                                    "type": "adventure_created",
                                    "adventure_id": adventure_id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"Error storing initial state: {e}")
                            # Continue without persistent storage
                    except ValueError as e:
                        error_message = f"Error initializing state: {e}"
                        logger.error(error_message)
                        await websocket.send_text(error_message)
                        await websocket.close(code=1001)
                        return  # Exit to prevent further processing
                # This 'else' corresponds to 'if current_state is None:'
                else:
                    # State exists (either loaded on connect or from previous loop iteration)
                    # Update it with the state received from the client
                    logger.debug("\nUpdating existing state from client message")
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()  # Get the updated state
                    logger.debug(
                        f"State after update from client - chapters: {len(state.chapters)}"
                    )

                # Ensure we have a valid state object after init or update
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
                    connection_data=connection_data,  # Pass connection data for persistence
                )

                if chapter_content is None:
                    continue

                # If story is complete, send completion data but don't end the connection
                # This allows processing the "reveal_summary" choice to generate Chapter 10 summary
                if is_story_complete:
                    await send_story_complete(
                        websocket=websocket,
                        state=state_manager.get_current_state(),
                        connection_data=connection_data,  # Pass connection data for persistence
                    )
                    continue  # Continue processing messages instead of breaking

                # Stream chapter content and send updates
                await stream_and_send_chapter(
                    websocket=websocket,
                    chapter_content=chapter_content,
                    sampled_question=sampled_question,
                    state=state_manager.get_current_state(),
                    # send_only_current_chapter=False # Flag removed
                )

                # After streaming the chapter, save the updated state to Supabase
                # This ensures we save after each significant state update
                if connection_data["adventure_id"]:
                    try:
                        current_state = state_manager.get_current_state()
                        if current_state:
                            await state_storage_service.store_state(
                                current_state.dict(),
                                adventure_id=connection_data["adventure_id"],
                                user_id=None,  # No authenticated user yet
                            )
                            logger.info(
                                f"Updated state in Supabase with ID: {connection_data['adventure_id']}"
                            )
                    except Exception as e:
                        logger.error(f"Error updating state in Supabase: {e}")
                        # Continue without persistent storage

            except Exception as e:
                logger.error(f"Error generating chapter: {e}")
                await websocket.send_text(
                    "\n\nAn error occurred while generating the story. Please try again."
                )
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
