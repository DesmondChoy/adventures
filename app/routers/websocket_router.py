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
):
    await websocket.accept()
    logger.info(
        f"WebSocket attempting connection with client_uuid: {client_uuid}"
    )  # Existing log
    logger.info(
        f"WebSocket connection established for story category: {story_category}, lesson topic: {lesson_topic}, client_uuid: {client_uuid}, difficulty: {difficulty}"
    )

    state_manager = AdventureStateManager()
    state_storage_service = StateStorageService()
    telemetry_service = TelemetryService()

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
                    logger.debug(
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
        logger.debug("No token provided, skipping JWT processing.")

    try:
        active_adventure_id = None
        # Check for existing active adventure
        if connection_data.get("user_id"):
            logger.debug(
                f"Checking for active adventure using user_id: {connection_data['user_id']}"
            )
            try:
                active_adventure_id = (
                    await state_storage_service.get_active_adventure_id(
                        user_id=connection_data["user_id"]
                    )
                )
                if active_adventure_id:
                    logger.debug(
                        f"Found active adventure {active_adventure_id} for user_id {connection_data['user_id']}"
                    )
                else:
                    logger.debug(
                        f"No active adventure found for user_id {connection_data['user_id']}. Will check client_uuid if present."
                    )
            except Exception as e:
                logger.error(
                    f"Error checking active adventure by user_id {connection_data['user_id']}: {e}"
                )

        if not active_adventure_id and client_uuid:
            logger.debug(
                f"Checking for active adventure using client_uuid: {client_uuid} (user_id lookup failed or no user_id)"
            )
            try:
                active_adventure_id = (
                    await state_storage_service.get_active_adventure_id(
                        client_uuid=client_uuid
                    )
                )
                if active_adventure_id:
                    logger.debug(
                        f"Found active adventure {active_adventure_id} for client_uuid {client_uuid}"
                    )
                else:
                    logger.debug(
                        f"No active adventure found for client_uuid {client_uuid} either."
                    )
            except Exception as e:
                logger.error(
                    f"Error checking active adventure by client_uuid {client_uuid}: {e}"
                )

        if active_adventure_id:
            connection_data["adventure_id"] = active_adventure_id
            await websocket.send_json(
                {
                    "type": "adventure_status",
                    "status": "existing",
                    "adventure_id": active_adventure_id,
                }
            )
        else:
            logger.info(
                f"No active adventure found for user_id {connection_data.get('user_id')} or client_uuid {client_uuid}"
            )
            await websocket.send_json({"type": "adventure_status", "status": "new"})

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
                    loaded_state_from_storage = (
                        await state_manager.reconstruct_state_from_storage(stored_state)
                    )
                    if loaded_state_from_storage:
                        logger.info(
                            "Successfully reconstructed and set state from storage upon connection."
                        )
                        await websocket.send_json(
                            {
                                "type": "adventure_loaded",
                                "adventure_id": connection_data["adventure_id"],
                                "current_chapter": loaded_state_from_storage.current_chapter_number,
                                "total_chapters": loaded_state_from_storage.story_length,
                            }
                        )
                        logger.info(
                            f"Loaded state indicates current chapter is {loaded_state_from_storage.current_chapter_number}"
                        )
                        if loaded_state_from_storage.chapters:
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
                                )
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
                                    elif chapter_to_display_data.content:
                                        resumption_content_dict = {
                                            "content": chapter_to_display_data.content,
                                            "choices": [
                                                choice.dict()
                                                for choice in chapter_to_display_data.choices
                                                or []
                                            ],
                                        }
                                    resumption_question_dict = (
                                        chapter_to_display_data.question
                                        if chapter_to_display_data.question
                                        else None
                                    )
                                    if resumption_content_dict:
                                        await stream_chapter_content(
                                            websocket=websocket,
                                            state=loaded_state_from_storage,
                                            adventure_id=connection_data.get(
                                                "adventure_id"
                                            ),
                                            story_category=story_category,
                                            lesson_topic=lesson_topic,
                                            connection_data=connection_data,
                                            is_resumption=True,
                                            resumption_chapter_content_dict=resumption_content_dict,
                                            resumption_sampled_question_dict=resumption_question_dict,
                                            resumption_chapter_number=chapter_to_display_data.chapter_number,
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
                    else:
                        logger.error(
                            f"Failed to reconstruct state from storage for ID: {connection_data['adventure_id']}. Will create new adventure."
                        )
                        connection_data["adventure_id"] = None
                else:
                    logger.warning(
                        f"No state found in storage for supposedly active ID: {connection_data['adventure_id']}. Will create new adventure."
                    )
                    connection_data["adventure_id"] = None
            except Exception as e:
                logger.error(f"Error loading state from storage upon connection: {e}")
                connection_data["adventure_id"] = None

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

            if not validated_state:
                logger.error("Missing state in message")
                await websocket.send_text("Missing state in message")
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
                    logger.debug(
                        f"Initializing state with total_chapters: {total_chapters}"
                    )
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
                    logger.debug("\nUpdating existing state from client message")
                    state_manager.update_state_from_client(validated_state)
                    state = state_manager.get_current_state()
                    logger.debug(
                        f"State after update from client - chapters: {len(state.chapters)}"
                    )

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
