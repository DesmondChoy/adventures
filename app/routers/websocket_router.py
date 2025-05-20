from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.models.story import ChapterType  # Added import
from app.services.adventure_state_manager import AdventureStateManager
from app.services.state_storage_service import StateStorageService
from app.services.websocket.stream_handler import (
    stream_chapter_content,
)  # Corrected import path
from app.services.websocket_service import (
    process_choice,
    # stream_and_send_chapter, # Now imported directly from stream_handler
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
                        # --- Start: Proactively send resumed chapter content ---
                        if loaded_state_from_storage.chapters:
                            # current_chapter_number is the NEXT chapter to be generated.
                            # So, the chapter the user was on is current_chapter_number - 1.
                            chapter_number_to_resume_display = (
                                loaded_state_from_storage.current_chapter_number - 1
                            )

                            if (
                                chapter_number_to_resume_display > 0
                                and chapter_number_to_resume_display
                                <= len(loaded_state_from_storage.chapters)
                            ):
                                chapter_to_display_data = (
                                    loaded_state_from_storage.chapters[
                                        chapter_number_to_resume_display - 1
                                    ]
                                )  # 0-indexed list

                                # Check if this chapter is incomplete (e.g., no response, not a conclusion)
                                # Assuming ChapterData has a 'response' attribute that's None or not set if incomplete.
                                # And ChapterData has 'chapter_type'.
                                if (
                                    chapter_to_display_data.response is None
                                    and chapter_to_display_data.chapter_type
                                    != ChapterType.CONCLUSION
                                ):
                                    logger.info(
                                        f"Resuming adventure: Re-sending content for Chapter {chapter_to_display_data.chapter_number} (which is {chapter_number_to_resume_display})"
                                    )

                                    resumption_content_dict = None
                                    if chapter_to_display_data.chapter_content:
                                        resumption_content_dict = chapter_to_display_data.chapter_content.dict()
                                    elif chapter_to_display_data.content:  # Fallback if chapter_content model isn't populated but raw content is
                                        resumption_content_dict = {
                                            "content": chapter_to_display_data.content,
                                            "choices": [
                                                choice.dict()
                                                for choice in chapter_to_display_data.choices
                                                or []
                                            ],
                                        }

                                    resumption_question_dict = (
                                        chapter_to_display_data.question  # Just pass the dict directly
                                        if chapter_to_display_data.question
                                        else None
                                    )

                                    if resumption_content_dict:
                                        await stream_chapter_content(  # Use the direct import
                                            websocket=websocket,
                                            state=loaded_state_from_storage,
                                            is_resumption=True,
                                            resumption_chapter_content_dict=resumption_content_dict,
                                            resumption_sampled_question_dict=resumption_question_dict,
                                            resumption_chapter_number=chapter_to_display_data.chapter_number,  # Use the actual chapter number from ChapterData
                                            resumption_chapter_type=chapter_to_display_data.chapter_type,
                                        )
                                        connection_data[
                                            "resumed_session_just_sent_chapter"
                                        ] = True
                                    else:
                                        logger.warning(
                                            f"Could not prepare resumption_content_dict for chapter {chapter_to_display_data.chapter_number}. Cannot resend."
                                        )
                                else:
                                    logger.info(
                                        f"Chapter {chapter_to_display_data.chapter_number} (to resume) already has a response or is a conclusion. Waiting for client message."
                                    )
                            else:
                                logger.warning(
                                    f"Calculated chapter_number_to_resume_display ({chapter_number_to_resume_display}) is out of bounds for loaded chapters ({len(loaded_state_from_storage.chapters)})."
                                )
                        else:
                            logger.warning(
                                "Loaded state has no chapters, cannot determine chapter to resume."
                            )
                        # --- End: Proactively send resumed chapter content ---
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

            # Extract message type, state and choice data
            message_type = data.get("type", "process_choice")  # Not really used anymore
            validated_state = data.get(
                "state"
            )  # This is the client's current view of the state, may not be used directly if server state is authoritative
            choice_data = data.get(
                "choice"
            )  # This is the primary input from the client

            # --- Start: Handle initial "start" message after resumption ---
            if connection_data.get("resumed_session_just_sent_chapter"):
                # Check if the client sent the typical "start" message upon connection
                # The exact structure of 'choice_data' for a "start" needs to be confirmed.
                # Assuming it's a simple string "start" or a dict like {"chosen_path": "start"}
                is_initial_start_message = False
                if isinstance(choice_data, str) and choice_data.lower() == "start":
                    is_initial_start_message = True
                elif (
                    isinstance(choice_data, dict)
                    and choice_data.get("chosen_path", "").lower() == "start"
                ):
                    is_initial_start_message = True

                if is_initial_start_message:
                    logger.info(
                        "Ignoring initial 'start' message from client after successful chapter resumption."
                    )
                    connection_data["resumed_session_just_sent_chapter"] = (
                        False  # Reset flag
                    )
                    # Client might send other info like 'state' along with 'start', but we primarily care about ignoring the 'start' action.
                    # We expect the next message to be the actual choice for the resumed chapter.
                    continue  # Wait for the next message
            # --- End: Handle initial "start" message after resumption ---

            # logger.debug(f"Received data: {data}") # Can be verbose

            # Debug logging for incoming data
            logger.debug("\n=== DEBUG: WebSocket Message (Post-Resumption Check) ===")
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
                if (
                    state is None
                ):  # Note: 'state' here is the same as 'current_state' after this block
                    logger.error("State is None after initialization/update.")
                    await websocket.send_text(
                        "An error occurred. Please restart the adventure."
                    )
                    continue

                current_state = state  # Ensure current_state is the definitive one for the checks below

                # --- NEW: Handle "start" message when already at CONCLUSION chapter ---
                if (
                    current_state
                    and current_state.chapters  # Ensure chapters list exists
                    and len(current_state.chapters) == current_state.story_length
                    and isinstance(choice_data, str)
                    and choice_data.lower() == "start"
                    and current_state.chapters[-1].chapter_type
                    == ChapterType.CONCLUSION
                ):
                    logger.info(
                        f"Resumed at CONCLUSION chapter (Chapter {len(current_state.chapters)} of {current_state.story_length}). Client sent 'start'. Re-sending story_complete."
                    )
                    await send_story_complete(
                        websocket=websocket,
                        state=current_state,
                        connection_data=connection_data,
                    )
                    # Reset the flag if it was set during proactive chapter sending,
                    # as we are now handling this "start" differently.
                    if "resumed_session_just_sent_chapter" in connection_data:
                        del connection_data["resumed_session_just_sent_chapter"]
                    continue  # Wait for the actual next client message (e.g., reveal_summary)
                # --- END NEW ---

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
                    # *** NEW: Save state before sending story_complete and continuing ***
                    if connection_data["adventure_id"]:
                        try:
                            current_state_for_completion = (
                                state_manager.get_current_state()
                            )
                            if current_state_for_completion:
                                # Ensure is_complete is still false here, it's set to true
                                # only when the summary is actually generated and saved.
                                # The store_state service should handle the is_complete flag
                                # based on the state's last chapter type if not explicitly passed.
                                # For this save, we are just recording that Chapter 10 has been reached.
                                await state_storage_service.store_state(
                                    current_state_for_completion.dict(),
                                    adventure_id=connection_data["adventure_id"],
                                    user_id=None,
                                    explicit_is_complete=False,  # Ensure not marked complete yet
                                )
                                logger.info(
                                    f"Saved state after CONCLUSION chapter (Chapter {len(current_state_for_completion.chapters)}) generated (is_complete=False), before story_complete message. Adventure ID: {connection_data['adventure_id']}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Error saving state before story_complete message: {e}"
                            )
                    # *** END NEW ***

                    await send_story_complete(
                        websocket=websocket,
                        state=state_manager.get_current_state(),  # state_manager.get_current_state() should be the same as current_state_for_completion
                        connection_data=connection_data,
                    )
                    continue  # Continue processing messages instead of breaking

                # Stream chapter content and send updates
                await stream_chapter_content(  # Corrected function name
                    websocket=websocket,
                    # chapter_content=chapter_content, # This was for the old signature, new signature takes state and models
                    # sampled_question=sampled_question, # This was for the old signature
                    state=state_manager.get_current_state(),
                    generated_chapter_content_model=chapter_content,  # Pass the Pydantic model
                    generated_sampled_question_dict=sampled_question,  # Pass the dict
                    is_resumption=False,  # Explicitly False for new chapters
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
                                # Default is_complete derivation is fine here
                            )
                            logger.info(
                                f"Updated state in Supabase with ID: {connection_data['adventure_id']} (after regular chapter stream)"
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
