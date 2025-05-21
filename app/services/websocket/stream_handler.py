from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket
import asyncio
import logging
import re
import os
import time  # Added import
from uuid import UUID

from app.models.story import (
    ChapterType,
    ChapterContent,
    AdventureState,
    StoryChoice,
)  # Changed ChapterChoice to StoryChoice

from .content_generator import clean_chapter_content
from .image_generator import start_image_generation_tasks, process_image_tasks
from app.services.telemetry_service import TelemetryService

# Constants for streaming optimization
WORD_BATCH_SIZE = 1  # Reduced to stream word by word
WORD_DELAY = 0.02  # Delay between words
PARAGRAPH_DELAY = 0.1  # Delay between paragraphs

logger = logging.getLogger("story_app")
telemetry_service = TelemetryService()


async def stream_chapter_content(
    websocket: WebSocket,
    state: AdventureState,
    adventure_id: Optional[str] = None,  # Added for telemetry
    story_category: Optional[str] = None,  # Added for telemetry
    lesson_topic: Optional[str] = None,  # Added for telemetry
    connection_data: Optional[Dict[str, Any]] = None,  # Added for storing start time
    # For non-resumption:
    generated_chapter_content_model: Optional[ChapterContent] = None,
    generated_sampled_question_dict: Optional[Dict[str, Any]] = None,
    # For resumption:
    is_resumption: bool = False,
    resumption_chapter_content_dict: Optional[Dict[str, Any]] = None,
    resumption_sampled_question_dict: Optional[Dict[str, Any]] = None,
    resumption_chapter_number: Optional[int] = None,
    resumption_chapter_type: Optional[ChapterType] = None,
) -> None:
    """Stream chapter content and send chapter data to the client.
    Handles both new chapter generation and resumption of an existing chapter.
    """
    final_chapter_content_pydantic: ChapterContent
    final_sampled_question_as_dict: Optional[Dict[str, Any]]
    current_chapter_number_to_send: int
    current_chapter_type_to_send: ChapterType
    content_to_stream: str
    image_tasks: List[asyncio.Task] = []

    if is_resumption:
        logger.info(
            f"Resuming chapter. Using provided chapter content and question data dicts for chapter {resumption_chapter_number}."
        )
        if (
            resumption_chapter_content_dict is None
            or resumption_chapter_number is None
            or resumption_chapter_type is None
        ):
            logger.error(
                "Resumption error: missing resumption_chapter_content_dict, resumption_chapter_number, or resumption_chapter_type."
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Failed to resume chapter: critical data missing.",
                }
            )
            return

        try:
            parsed_choices_for_resumption = []
            raw_choices = resumption_chapter_content_dict.get("choices", [])
            if raw_choices:  # Ensure raw_choices is not None
                for choice_data in raw_choices:
                    if (
                        isinstance(choice_data, dict)
                        and "text" in choice_data
                        and "next_chapter" in choice_data
                    ):
                        parsed_choices_for_resumption.append(
                            StoryChoice(  # Changed ChapterChoice to StoryChoice
                                text=choice_data["text"],
                                next_chapter=str(choice_data["next_chapter"]),
                            )
                        )
                    elif isinstance(
                        choice_data,
                        StoryChoice,  # Changed ChapterChoice to StoryChoice
                    ):  # Should not happen if .dict() was called from Pydantic model
                        parsed_choices_for_resumption.append(choice_data)
                    else:
                        logger.warning(
                            f"Skipping invalid choice data during resumption: {choice_data}"
                        )

            final_chapter_content_pydantic = ChapterContent(
                content=resumption_chapter_content_dict.get("content", ""),
                choices=parsed_choices_for_resumption,
            )
            final_sampled_question_as_dict = resumption_sampled_question_dict

            current_chapter_number_to_send = resumption_chapter_number
            current_chapter_type_to_send = resumption_chapter_type

        except Exception as e:
            logger.error(
                f"Error reconstructing ChapterContent from dict during resumption: {e}",
                exc_info=True,
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Failed to resume chapter: content parsing error.",
                }
            )
            return

        content_to_stream = clean_chapter_content(
            final_chapter_content_pydantic.content
        )
        logger.info(
            f"Skipping image generation for resumed chapter {current_chapter_number_to_send}"
        )

    else:  # Not resumption
        if generated_chapter_content_model is None:
            logger.error("Non-resumption call missing generated_chapter_content_model.")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Internal server error: missing chapter data for streaming.",
                }
            )
            return
        final_chapter_content_pydantic = generated_chapter_content_model
        final_sampled_question_as_dict = generated_sampled_question_dict

        current_chapter_number_to_send = len(state.chapters)
        logger.debug(
            f"New chapter number: {current_chapter_number_to_send}. State has {len(state.chapters)} existing chapters."
        )
        if current_chapter_number_to_send < 1:
            logger.warning(
                f"Invalid chapter number {current_chapter_number_to_send} for new chapter, setting to 1"
            )
            current_chapter_number_to_send = 1

        chapter_type_index = current_chapter_number_to_send - 1
        if chapter_type_index < 0 or chapter_type_index >= len(
            state.planned_chapter_types
        ):
            logger.error(
                f"Chapter type index {chapter_type_index} out of range for planned_chapter_types with length {len(state.planned_chapter_types)}"
            )
            current_chapter_type_to_send = ChapterType.STORY  # Fallback
        else:
            planned_type = state.planned_chapter_types[chapter_type_index]
            if isinstance(planned_type, ChapterType):
                current_chapter_type_to_send = planned_type
            else:  # Assuming it's a string from older state or direct manipulation
                current_chapter_type_to_send = ChapterType(str(planned_type).lower())

        content_to_stream = clean_chapter_content(
            final_chapter_content_pydantic.content
        )

        # Start image generation for new chapters
        try:
            image_tasks = await start_image_generation_tasks(
                current_chapter_number_to_send,
                current_chapter_type_to_send,
                final_chapter_content_pydantic,
                state,
            )
            logger.info(
                f"Started {len(image_tasks)} image generation tasks for chapter {current_chapter_number_to_send}"
            )
        except Exception as e:
            logger.error(
                f"Error starting image generation tasks: {str(e)}", exc_info=True
            )
            image_tasks = []

    # Stream chapter content
    await stream_text_content(content_to_stream, websocket)

    # Send complete chapter data with choices included
    await send_chapter_data(
        content_to_stream,
        final_chapter_content_pydantic,
        current_chapter_type_to_send,
        current_chapter_number_to_send,
        final_sampled_question_as_dict,
        state,
        websocket,
    )

    # Also send choices separately for backward compatibility
    await websocket.send_json(
        {
            "type": "choices",
            "choices": [
                {"text": choice.text, "id": str(choice.next_chapter)}
                for choice in final_chapter_content_pydantic.choices
            ],
        }
    )

    # Hide loader after streaming content, but before waiting for image tasks
    await websocket.send_json({"type": "hide_loader"})

    # If we have image tasks (only if not is_resumption), wait for them to complete and send updates
    if not is_resumption:
        try:
            if image_tasks:
                await process_image_tasks(
                    image_tasks, current_chapter_number_to_send, websocket
                )
                logger.info(
                    f"Processed image tasks for chapter {current_chapter_number_to_send}"
                )
            else:
                logger.warning(
                    f"No image tasks available for chapter {current_chapter_number_to_send} (non-resumption), using fallback image"
                )
                await send_fallback_image(
                    state, current_chapter_number_to_send, websocket
                )
        except Exception as e:
            logger.error(f"Error processing image tasks: {str(e)}", exc_info=True)
            await send_fallback_image(state, current_chapter_number_to_send, websocket)
    elif is_resumption:
        logger.info(
            f"Image processing skipped for resumed chapter {current_chapter_number_to_send}."
        )
        # Optionally, send a message or ensure client handles no new image for resumed chapter

    # Log chapter_viewed event
    try:
        event_metadata = {
            "chapter_number": current_chapter_number_to_send,
            "chapter_type": current_chapter_type_to_send.value,
            "story_category": story_category,  # Use passed argument
            "lesson_topic": lesson_topic,  # Use passed argument
            "is_resumption": is_resumption,
            "client_uuid": state.metadata.get("client_uuid"),
        }
        # Remove None values from metadata to keep it clean
        event_metadata = {k: v for k, v in event_metadata.items() if v is not None}

        await telemetry_service.log_event(
            event_name="chapter_viewed",
            adventure_id=UUID(adventure_id) if adventure_id else None,
            user_id=None,  # No authenticated user_id yet
            metadata=event_metadata,
            chapter_type=current_chapter_type_to_send.value,  # Added
            chapter_number=current_chapter_number_to_send,  # Added
        )
        logger.info(
            f"Logged 'chapter_viewed' event for adventure ID: {adventure_id}, chapter: {current_chapter_number_to_send}, type: {current_chapter_type_to_send.value}"
        )
    except Exception as tel_e:
        logger.error(f"Error logging 'chapter_viewed' event: {tel_e}")

    # Store chapter start time for duration calculation
    if connection_data and isinstance(connection_data, dict):
        connection_data["current_chapter_start_time_ms"] = int(time.time() * 1000)
        logger.debug(
            f"Stored chapter start time for adventure_id {adventure_id}, chapter {current_chapter_number_to_send}"
        )
    else:
        logger.warning(
            f"'connection_data' not available or not a dict in stream_handler for adventure {adventure_id}, chapter {current_chapter_number_to_send}, cannot store chapter start time."
        )


async def send_fallback_image(
    state: AdventureState, chapter_number: int, websocket: WebSocket
) -> None:
    """Send a fallback image for the chapter from static files.

    This function tries different static image files in order of preference:
    1. Story category specific image
    2. Lesson topic specific image
    3. Any available story image as a last resort

    Args:
        state: The current adventure state
        chapter_number: The chapter number
        websocket: The WebSocket connection
    """
    logger.info(f"Sending fallback image for chapter {chapter_number}")

    # Different image sources in order of preference
    image_paths = []

    # Get the story category (which might be in different formats)
    story_category = None
    if hasattr(state, "storyCategory"):
        story_category = getattr(state, "storyCategory", "")
    elif hasattr(state, "story_category"):
        story_category = getattr(state, "story_category", "")
    elif hasattr(state, "metadata") and "story_category" in state.metadata:
        story_category = state.metadata["story_category"]

    # 1. Try story category specific image
    if story_category:
        logger.info(f"Found story category: {story_category}")
        # Try different formats and casing
        image_paths.append(f"app/static/images/stories/{story_category}.jpg")
        image_paths.append(f"app/static/images/stories/{story_category.lower()}.jpg")

        # Common story categories in the standard format
        story_mappings = {
            "enchanted_forest": "enchanted_forest_tales",
            "enchanted forest": "enchanted_forest_tales",
            "forest": "enchanted_forest_tales",
            "circus": "circus_and_carnival_capers",
            "carnival": "circus_and_carnival_capers",
            "jade": "jade_mountain",
            "mountain": "jade_mountain",
            "festival": "festival_of_lights_and_colors",
            "lights": "festival_of_lights_and_colors",
        }

        # Try to map the story category to a standard filename
        for key, value in story_mappings.items():
            if key in story_category.lower():
                image_paths.append(f"app/static/images/stories/{value}.jpg")

    # 2. Try lesson topic specific image
    lesson_topic = getattr(state, "lessonTopic", "")
    if lesson_topic:
        logger.info(f"Found lesson topic: {lesson_topic}")
        image_paths.append(f"app/static/images/lessons/{lesson_topic}.jpg")

        # Try with spaces instead of underscores
        if "_" in lesson_topic:
            image_paths.append(
                f"app/static/images/lessons/{lesson_topic.replace('_', ' ')}.jpg"
            )

        # Try with capitalization
        words = lesson_topic.split("_")
        capitalized = " ".join(word.capitalize() for word in words)
        image_paths.append(f"app/static/images/lessons/{capitalized}.jpg")

    # 3. Try any story image as last resort
    image_paths.extend(
        [
            "app/static/images/stories/enchanted_forest_tales.jpg",
            "app/static/images/stories/circus_and_carnival_capers.jpg",
            "app/static/images/stories/jade_mountain.jpg",
            "app/static/images/stories/festival_of_lights_and_colors.jpg",
        ]
    )

    # 4. Try any lesson image as a very last resort
    image_paths.extend(
        [
            "app/static/images/lessons/Farm Animals.jpg",
            "app/static/images/lessons/Human Body.jpg",
            "app/static/images/lessons/Singapore History.jpg",
        ]
    )

    # Try each path in order until one works
    logger.info(f"Trying {len(image_paths)} possible image paths")
    for path in image_paths:
        try:
            logger.debug(f"Checking path: {path}")
            if os.path.exists(path):
                logger.info(f"Found fallback image at {path}")
                import base64

                with open(path, "rb") as img_file:
                    img_data = img_file.read()
                    fallback_image = base64.b64encode(img_data).decode("utf-8")
                    await websocket.send_json(
                        {
                            "type": "chapter_image_update",
                            "chapter_number": chapter_number,
                            "image_data": fallback_image,
                        }
                    )
                    logger.info(
                        f"Successfully sent fallback image ({len(img_data)} bytes) for chapter {chapter_number}"
                    )
                    return  # Exit after successfully sending an image
        except Exception as img_error:
            logger.error(f"Error with fallback image path {path}: {str(img_error)}")
            continue

    logger.error("No valid fallback image found - tried all possible paths")


async def stream_summary_content(summary_content: str, websocket: WebSocket) -> None:
    """Stream summary content to the client."""
    await websocket.send_json({"type": "summary_start"})

    # Split content into paragraphs and stream
    paragraphs = [p.strip() for p in summary_content.split("\n\n") if p.strip()]

    for paragraph in paragraphs:
        # For headings, send them as a whole
        if paragraph.startswith("#"):
            await websocket.send_text(paragraph + "\n\n")
            await asyncio.sleep(PARAGRAPH_DELAY)
            continue

        # For regular paragraphs, stream word by word
        words = paragraph.split()
        for word in words:
            await websocket.send_text(word + " ")
            await asyncio.sleep(WORD_DELAY)

        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)


async def stream_conclusion_content(content: str, websocket: WebSocket) -> None:
    """Stream conclusion chapter content to the client."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    # Check for dialogue patterns that might be affected by streaming
    for i, paragraph in enumerate(paragraphs):
        # Check if this paragraph starts with a dialogue verb that might indicate a missing character name
        if i == 0 and re.match(
            r"^(chirped|said|whispered|shouted|called|murmured|exclaimed|replied|asked|answered|responded)\b",
            paragraph,
        ):
            logger.warning(
                "Detected conclusion chapter starting with dialogue verb - possible missing character name"
            )
            # We'll log this but continue processing normally

        # Check if paragraph starts with dialogue (quotation mark)
        if paragraph.strip().startswith('"'):
            # For paragraphs starting with dialogue, handle differently to preserve opening quotes
            words = paragraph.split()
            if len(words) > 0:
                # Find the first word with the quotation mark
                first_word = words[0]

                # Send the first word with its quotation mark intact
                await websocket.send_text(first_word + " ")
                await asyncio.sleep(WORD_DELAY)

                # Then stream the rest of the words normally
                for i in range(1, len(words), WORD_BATCH_SIZE):
                    batch = " ".join(words[i : i + WORD_BATCH_SIZE])
                    await websocket.send_text(batch + " ")
                    await asyncio.sleep(WORD_DELAY)
            else:
                # Fallback if splitting doesn't work as expected
                await websocket.send_text(paragraph)
                await asyncio.sleep(PARAGRAPH_DELAY)
        else:
            # For non-dialogue paragraphs, stream normally word by word
            words = paragraph.split()
            for i in range(0, len(words), WORD_BATCH_SIZE):
                batch = " ".join(words[i : i + WORD_BATCH_SIZE])
                await websocket.send_text(batch + " ")
                await asyncio.sleep(WORD_DELAY)

        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)


async def stream_text_content(content: str, websocket: WebSocket) -> None:
    """Stream chapter content word by word to the client."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    # Check for dialogue patterns that might be affected by streaming
    for i, paragraph in enumerate(paragraphs):
        # Check if this paragraph starts with a dialogue verb that might indicate a missing character name
        if i == 0 and re.match(
            r"^(chirped|said|whispered|shouted|called|murmured|exclaimed|replied|asked|answered|responded)\b",
            paragraph,
        ):
            logger.warning(
                "Detected paragraph starting with dialogue verb - possible missing character name"
            )
            # We'll log this but continue processing normally

        # Check if paragraph starts with dialogue (quotation mark)
        if paragraph.strip().startswith('"'):
            # For paragraphs starting with dialogue, handle differently to preserve opening quotes
            words = paragraph.split()
            if len(words) > 0:
                # Find the first word with the quotation mark
                first_word = words[0]

                # Send the first word with its quotation mark intact
                await websocket.send_text(first_word + " ")
                await asyncio.sleep(WORD_DELAY)

                # Then stream the rest of the words normally
                for word in words[1:]:
                    await websocket.send_text(word + " ")
                    await asyncio.sleep(WORD_DELAY)
            else:
                # Fallback if splitting doesn't work as expected
                await websocket.send_text(paragraph)
                await asyncio.sleep(PARAGRAPH_DELAY)
        else:
            # For non-dialogue paragraphs, stream normally word by word
            words = paragraph.split()
            for word in words:
                await websocket.send_text(word + " ")
                await asyncio.sleep(WORD_DELAY)

        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)


async def send_chapter_data(
    content_to_stream: str,
    chapter_content: ChapterContent,
    chapter_type: ChapterType,
    chapter_number: int,
    sampled_question: Optional[Dict[str, Any]],
    state: AdventureState,
    websocket: WebSocket,
) -> None:
    """Send complete chapter data to the client."""
    chapter_data = {
        "type": "chapter_update",
        "state": {
            "current_chapter_id": state.current_chapter_id,
            "current_chapter": {
                "chapter_number": chapter_number,
                "content": content_to_stream,
                "chapter_type": chapter_type.value,  # Add chapter type to response
                "chapter_content": {
                    "content": chapter_content.content,
                    "choices": [
                        {"text": choice.text, "next_chapter": choice.next_chapter}
                        for choice in chapter_content.choices
                    ],
                },
                "question": sampled_question,
            },
            # Include chapter_summaries in the response for simulation logging
            "chapter_summaries": state.chapter_summaries,
        },
    }
    logger.debug("\n=== DEBUG: Chapter Update Message ===")
    logger.debug(f"Chapter number: {chapter_number}")
    logger.debug(f"Chapter type: {chapter_type.value}")
    logger.debug(f"Has question: {sampled_question is not None}")
    logger.debug("===================================\n")
    await websocket.send_json(chapter_data)
