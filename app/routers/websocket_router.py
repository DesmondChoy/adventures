from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging
import os
import jwt  # PyJWT
from typing import Optional
from uuid import UUID
from app.models.story import ChapterType
from app.services.adventure_state_manager import AdventureStateManager
from app.services.state_storage_service import StateStorageService
from app.services.telemetry_service import TelemetryService
from app.services.websocket.stream_handler import (
    stream_chapter_content,
)
from app.services.websocket_service import (
    process_choice,
    send_story_complete,
)

router = APIRouter()
logger = logging.getLogger("story_app")


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(
    websocket: WebSocket,
    story_category: str,
    lesson_topic: str,
    client_uuid: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    resume_adventure_id: Optional[str] = Query(
        None
    ),  # New parameter for specific resumption
):
    await websocket.accept()
    logger.info(
        f"WebSocket attempting connection with client_uuid: {client_uuid}, resume_adventure_id: {resume_adventure_id}"
    )
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}, client_uuid: {client_uuid}, difficulty: {difficulty}, resume_adventure_id: {resume_adventure_id}"
    )

    state_manager = AdventureStateManager()
    state_storage_service = StateStorageService()

    # Lazy instantiation to avoid environment variable loading issues during import
    def get_telemetry_service():
        return TelemetryService()

    telemetry_service = get_telemetry_service()

    connection_data = {
        "adventure_id": None,
        "client_uuid": client_uuid,
        "user_id": None,
    }

    # JWT Processing Block
    if token:
        supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if supabase_jwt_secret:
            try:
                payload = jwt.decode(
                    token,
                    supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
                user_id_from_token_str = payload.get("sub")
                if user_id_from_token_str:
                    connection_data["user_id"] = UUID(user_id_from_token_str)
                    logger.info(
                        f"Authenticated user via JWT: {connection_data['user_id']}"
                    )
                else:
                    logger.warning("JWT decoded but 'sub' (user_id) claim is missing.")
            except jwt.ExpiredSignatureError:
                logger.warning("JWT ExpiredSignatureError")
            except jwt.InvalidTokenError as e:
                logger.warning(f"JWT InvalidTokenError: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during JWT decoding: {e}")
        else:
            logger.error("SUPABASE_JWT_SECRET is missing or empty. Cannot decode JWT.")
    else:
        logger.info("No token provided, skipping JWT processing.")

    try:
        loaded_state_from_storage = None

        if resume_adventure_id:
            logger.info(
                f"Attempting to resume specific adventure_id: {resume_adventure_id}"
            )
            connection_data["adventure_id"] = resume_adventure_id
            try:
                stored_state = await state_storage_service.get_state(
                    resume_adventure_id
                )
                if stored_state:
                    # TODO: Add user_id validation here. Ensure token's user_id matches stored_state's user_id if both exist.
                    # For now, RLS policies are the primary guard.
                    current_user_id = connection_data.get("user_id")
                    adventure_owner_id_str = stored_state.get("metadata", {}).get(
                        "user_id"
                    )  # Assuming user_id is in metadata or top level of state_data
                    if (
                        not adventure_owner_id_str and "user_id" in stored_state
                    ):  # Check top level if not in metadata
                        adventure_owner_id_str = stored_state.get("user_id")

                    can_load = False
                    if adventure_owner_id_str is None:  # Guest adventure
                        can_load = True
                        logger.info(f"Resuming guest adventure {resume_adventure_id}.")
                    elif current_user_id and adventure_owner_id_str == str(
                        current_user_id
                    ):
                        can_load = True
                        logger.info(
                            f"User {current_user_id} confirmed owner of adventure {resume_adventure_id}."
                        )
                    else:
                        logger.warning(
                            f"User {current_user_id} is not the owner of adventure {resume_adventure_id} (owner: {adventure_owner_id_str}). Denying direct load via ID."
                        )
                        # This case should ideally be prevented by RLS or frontend not allowing this.
                        # If it happens, treat as if no adventure found.
                        connection_data["adventure_id"] = None  # Clear it
                        # Fall through to normal "find active or new" logic

                    if can_load:
                        logger.info(
                            f"Reconstructing state from storage for specific ID: {resume_adventure_id}"
                        )
                        loaded_state_from_storage = (
                            await state_manager.reconstruct_state_from_storage(
                                stored_state
                            )
                        )
                        if loaded_state_from_storage:
                            logger.info(
                                "Successfully reconstructed state for specific resumption."
                            )
                            # Story category and lesson topic might differ from URL if resuming specific ID
                            # Update them from the loaded state for consistency in subsequent calls
                            story_category = loaded_state_from_storage.metadata.get(
                                "story_category", story_category
                            )
                            lesson_topic = loaded_state_from_storage.metadata.get(
                                "lesson_topic", lesson_topic
                            )
                            logger.info(
                                f"Updated story_category to '{story_category}' and lesson_topic to '{lesson_topic}' from resumed state."
                            )
                        else:
                            logger.error(
                                f"Failed to reconstruct state for specific ID: {resume_adventure_id}. Treating as new."
                            )
                            connection_data["adventure_id"] = (
                                None  # Clear it to allow new adventure creation
                            )
                    # If can_load is false, loaded_state_from_storage remains None, will proceed to find/create new.
                else:
                    logger.warning(
                        f"No state found in storage for specific resume_adventure_id: {resume_adventure_id}. Will try to find active or create new."
                    )
                    connection_data["adventure_id"] = None  # Clear it
            except Exception as e:
                logger.error(
                    f"Error loading state for specific resume_adventure_id {resume_adventure_id}: {e}"
                )
                connection_data["adventure_id"] = None  # Clear it

        if (
            not loaded_state_from_storage
        ):  # If not resuming specific or specific resumption failed
            active_adventure_id = None
            # Check for existing active adventure (original logic)
            if connection_data.get("user_id"):
                try:
                    active_adventure_id = (
                        await state_storage_service.get_active_adventure_id(
                            user_id=connection_data["user_id"],
                            story_category=story_category,
                            lesson_topic=lesson_topic,
                        )
                    )
                    if active_adventure_id:
                        logger.info(
                            f"Found active adventure {active_adventure_id} for user_id {connection_data['user_id']}"
                        )
                    else:
                        logger.info(
                            f"No active adventure found for user_id {connection_data['user_id']}. Will check client_uuid if present."
                        )
                except Exception as e:
                    logger.error(
                        f"Error checking active adventure by user_id {connection_data['user_id']}: {e}"
                    )

            # SECURITY FIX: Only fall back to client_uuid if user is NOT authenticated
            if (
                not active_adventure_id
                and client_uuid
                and not connection_data.get("user_id")
            ):
                try:
                    active_adventure_id = (
                        await state_storage_service.get_active_adventure_id(
                            client_uuid=client_uuid,
                            story_category=story_category,
                            lesson_topic=lesson_topic,
                        )
                    )
                    if active_adventure_id:
                        logger.info(
                            f"Found active adventure {active_adventure_id} for client_uuid {client_uuid} (guest user)"
                        )
                    else:
                        logger.info(
                            f"No active adventure found for client_uuid {client_uuid} either."
                        )
                except Exception as e:
                    logger.error(
                        f"Error checking active adventure by client_uuid {client_uuid}: {e}"
                    )
            elif (
                not active_adventure_id
                and client_uuid
                and connection_data.get("user_id")
            ):
                logger.info(
                    f"User {connection_data['user_id']} is authenticated - skipping client_uuid fallback for security"
                )

            if active_adventure_id:
                connection_data["adventure_id"] = active_adventure_id
                # Attempt to load this active adventure's state
                try:
                    stored_state = await state_storage_service.get_state(
                        active_adventure_id
                    )
                    if stored_state:
                        logger.info(
                            f"Reconstructing state from storage for active ID: {active_adventure_id}"
                        )
                        loaded_state_from_storage = (
                            await state_manager.reconstruct_state_from_storage(
                                stored_state
                            )
                        )
                        if loaded_state_from_storage:
                            logger.info(
                                "Successfully reconstructed state for active adventure."
                            )
                            story_category = loaded_state_from_storage.metadata.get(
                                "story_category", story_category
                            )
                            lesson_topic = loaded_state_from_storage.metadata.get(
                                "lesson_topic", lesson_topic
                            )
                        else:
                            logger.error(
                                f"Failed to reconstruct state for active ID: {active_adventure_id}. Will create new."
                            )
                            connection_data["adventure_id"] = None
                    else:
                        logger.warning(
                            f"No state found for active ID: {active_adventure_id}. Will create new."
                        )
                        connection_data["adventure_id"] = None
                except Exception as e:
                    logger.error(
                        f"Error loading state for active adventure {active_adventure_id}: {e}"
                    )
                    connection_data["adventure_id"] = None
            else:  # No active_adventure_id found by any means
                logger.info(
                    f"No active adventure found for user_id {connection_data.get('user_id')} or client_uuid {client_uuid}. A new adventure will be created on first client message."
                )

        # Send status based on whether an adventure was loaded (either specific or active)
        if loaded_state_from_storage and connection_data["adventure_id"]:
            # Determine the correct chapter number to display to the user
            display_chapter_number = loaded_state_from_storage.current_chapter_number

            # Check if we'll be re-sending a chapter for resumption
            if loaded_state_from_storage.chapters:
                chapter_number_to_resume_display = (
                    loaded_state_from_storage.current_chapter_number - 1
                )
                if (
                    0
                    < chapter_number_to_resume_display
                    <= len(loaded_state_from_storage.chapters)
                ):
                    chapter_to_display_data = loaded_state_from_storage.chapters[
                        chapter_number_to_resume_display - 1
                    ]
                    if (
                        chapter_to_display_data.response is None
                        and chapter_to_display_data.chapter_type
                        != ChapterType.CONCLUSION
                    ):
                        # We'll be re-sending this chapter, so user will see this chapter number
                        display_chapter_number = chapter_to_display_data.chapter_number

            await websocket.send_json(
                {
                    "type": "adventure_loaded",  # Changed from adventure_status for clarity
                    "status": "existing_loaded",  # More specific status
                    "adventure_id": connection_data["adventure_id"],
                    "current_chapter": display_chapter_number,
                    "total_chapters": loaded_state_from_storage.story_length,
                }
            )
            logger.info(
                f"Loaded state indicates current chapter is {loaded_state_from_storage.current_chapter_number}, displaying chapter {display_chapter_number} to user"
            )
            # Resend last chapter content if needed (existing logic)
            if loaded_state_from_storage.chapters:
                chapter_number_to_resume_display = (
                    loaded_state_from_storage.current_chapter_number - 1
                )
                if (
                    0
                    < chapter_number_to_resume_display
                    <= len(loaded_state_from_storage.chapters)
                ):
                    chapter_to_display_data = loaded_state_from_storage.chapters[
                        chapter_number_to_resume_display - 1
                    ]
                    if (
                        chapter_to_display_data.response is None
                        and chapter_to_display_data.chapter_type
                        != ChapterType.CONCLUSION
                    ):
                        logger.info(
                            f"Resuming adventure: Re-sending content for Chapter {chapter_to_display_data.chapter_number}"
                        )
                        resumption_content_dict = (
                            chapter_to_display_data.chapter_content.dict()
                            if chapter_to_display_data.chapter_content
                            else {
                                "content": chapter_to_display_data.content,
                                "choices": [
                                    c.dict()
                                    for c in chapter_to_display_data.choices or []
                                ],
                            }
                        )
                        resumption_question_dict = (
                            chapter_to_display_data.question
                            if chapter_to_display_data.question
                            else None
                        )
                        if resumption_content_dict:
                            await stream_chapter_content(
                                websocket=websocket,
                                state=loaded_state_from_storage,
                                adventure_id=connection_data.get("adventure_id"),
                                story_category=story_category,
                                lesson_topic=lesson_topic,
                                connection_data=connection_data,
                                is_resumption=True,
                                resumption_chapter_content_dict=resumption_content_dict,
                                resumption_sampled_question_dict=resumption_question_dict,
                                resumption_chapter_number=chapter_to_display_data.chapter_number,
                                resumption_chapter_type=chapter_to_display_data.chapter_type,
                            )
                            connection_data["resumed_session_just_sent_chapter"] = True
                        else:
                            logger.warning(
                                f"Could not prepare resumption_content_dict for chapter {chapter_to_display_data.chapter_number}."
                            )
                    else:
                        logger.info(
                            f"Chapter {chapter_to_display_data.chapter_number} (to resume) already has a response or is a conclusion."
                        )
                else:
                    logger.warning(
                        f"Calculated chapter_number_to_resume_display ({chapter_number_to_resume_display}) is out of bounds."
                    )
            else:
                logger.warning(
                    "Loaded state has no chapters, cannot determine chapter to resume."
                )
        else:  # No adventure loaded, will be new
            await websocket.send_json({"type": "adventure_status", "status": "new"})

        while True:
            data = await websocket.receive_json()
            validated_state = data.get("state")
            choice_data = data.get("choice")

            if connection_data.get("resumed_session_just_sent_chapter"):
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
                    connection_data["resumed_session_just_sent_chapter"] = False
                    continue

            if not validated_state:
                logger.error("Missing state in message")
                await websocket.send_text(
                    "<Current image unavailable after reconnecting>"
                )
                continue
            if not choice_data:
                logger.error("Missing choice in message")
                await websocket.send_text("Missing choice in message")
                continue

            try:
                current_state = state_manager.get_current_state()
                if current_state is None:
                    if connection_data["adventure_id"]:
                        logger.warning(
                            f"State is None but adventure_id {connection_data['adventure_id']} exists. Re-initializing."
                        )
                        connection_data["adventure_id"] = None
                    total_chapters = validated_state.get("story_length", 10)
                    try:
                        state = state_manager.initialize_state(
                            total_chapters, lesson_topic, story_category, difficulty
                        )
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
                        try:
                            adventure_id = await state_storage_service.store_state(
                                state.dict(),
                                user_id=connection_data.get("user_id"),
                                lesson_topic=lesson_topic,
                            )
                            connection_data["adventure_id"] = adventure_id
                            logger.info(
                                f"Stored new state with ID: {adventure_id} (user_id: {connection_data.get('user_id')})"
                            )
                            try:
                                await telemetry_service.log_event(
                                    event_name="adventure_started",
                                    adventure_id=UUID(adventure_id)
                                    if adventure_id
                                    else None,
                                    user_id=connection_data.get("user_id"),
                                    metadata={
                                        "story_category": story_category,
                                        "lesson_topic": lesson_topic,
                                        "difficulty": difficulty,
                                        "client_uuid": client_uuid,
                                    },
                                    chapter_type=None,
                                    chapter_number=None,
                                )
                                logger.info(
                                    f"Logged 'adventure_started' event for adventure ID: {adventure_id}"
                                )
                            except Exception as tel_e:
                                logger.error(
                                    f"Error logging 'adventure_started' event: {tel_e}"
                                )
                            await websocket.send_json(
                                {
                                    "type": "adventure_created",
                                    "adventure_id": adventure_id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"Error storing initial state: {e}")
                    except ValueError as e:
                        error_message = f"Error initializing state: {e}"
                        logger.error(error_message)
                        await websocket.send_text(error_message)
                        await websocket.close(code=1001)
                        return
                else:
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()

                if state is None:
                    logger.error("State is None after initialization/update.")
                    await websocket.send_text(
                        "An error occurred. Please restart the adventure."
                    )
                    continue
                current_state = state

                if (
                    current_state
                    and current_state.chapters
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
                    if "resumed_session_just_sent_chapter" in connection_data:
                        del connection_data["resumed_session_just_sent_chapter"]
                    continue

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
                    connection_data=connection_data,
                )

                if chapter_content is None:
                    continue

                if is_story_complete:
                    if connection_data["adventure_id"]:
                        try:
                            current_state_for_completion = (
                                state_manager.get_current_state()
                            )
                            if current_state_for_completion:
                                await state_storage_service.store_state(
                                    current_state_for_completion.dict(),
                                    adventure_id=connection_data["adventure_id"],
                                    user_id=connection_data.get("user_id"),
                                    explicit_is_complete=False,
                                )
                                logger.info(
                                    f"Saved state after CONCLUSION chapter (Chapter {len(current_state_for_completion.chapters)}) generated (is_complete=False), before story_complete message. Adventure ID: {connection_data['adventure_id']}, User ID: {connection_data.get('user_id')}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Error saving state before story_complete message: {e}"
                            )
                    await send_story_complete(
                        websocket=websocket,
                        state=state_manager.get_current_state(),
                        connection_data=connection_data,
                    )
                    continue

                await stream_chapter_content(
                    websocket=websocket,
                    state=state_manager.get_current_state(),
                    adventure_id=connection_data.get("adventure_id"),
                    story_category=story_category,
                    lesson_topic=lesson_topic,
                    connection_data=connection_data,
                    generated_chapter_content_model=chapter_content,
                    generated_sampled_question_dict=sampled_question,
                    is_resumption=False,
                )

                if connection_data["adventure_id"]:
                    try:
                        current_state = state_manager.get_current_state()
                        if current_state:
                            await state_storage_service.store_state(
                                current_state.dict(),
                                adventure_id=connection_data["adventure_id"],
                                user_id=connection_data.get("user_id"),
                            )
                            logger.info(
                                f"Updated state in Supabase with ID: {connection_data['adventure_id']}, User ID: {connection_data.get('user_id')} (after regular chapter stream)"
                            )
                    except Exception as e:
                        logger.error(f"Error updating state in Supabase: {e}")
            except Exception as e:
                logger.error(f"Error generating chapter: {e}")
                await websocket.send_text(
                    "\n\nAn error occurred while generating the story. Please try again."
                )
                break
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except (
        Exception
    ) as e:  # Catch any other unexpected errors during setup or main loop
        logger.error(f"Unexpected error in WebSocket handler: {e}", exc_info=True)
        try:
            await websocket.close(code=1011)  # Internal Server Error
        except Exception:
            pass  # Ignore errors during close if connection already broken
