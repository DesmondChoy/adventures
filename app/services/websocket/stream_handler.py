from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket
import asyncio
import logging
import re
import os

from app.models.story import ChapterType, ChapterContent, AdventureState

from .content_generator import clean_chapter_content
from .image_generator import start_image_generation_tasks, process_image_tasks

# Constants for streaming optimization
WORD_BATCH_SIZE = 1  # Reduced to stream word by word
WORD_DELAY = 0.02  # Delay between words
PARAGRAPH_DELAY = 0.1  # Delay between paragraphs

logger = logging.getLogger("story_app")


async def stream_chapter_content(
    websocket: WebSocket,
    chapter_content: ChapterContent,
    sampled_question: Optional[Dict[str, Any]],
    state: AdventureState,
) -> None:
    """Stream chapter content and send chapter data to the client."""
    # Use the Pydantic validator to clean the content before streaming
    content_to_stream = clean_chapter_content(chapter_content.content)

    # Get chapter type for current chapter
    # The current chapter has already been added to the state at this point
    current_chapter_number = len(state.chapters)

    # Debug log to check chapter number calculation
    logger.debug(f"Current chapter number: {current_chapter_number}")
    logger.debug(f"State has {len(state.chapters)} existing chapters")

    # Make sure we have a valid chapter number (never 0)
    if current_chapter_number < 1:
        logger.warning(f"Invalid chapter number {current_chapter_number}, setting to 1")
        current_chapter_number = 1

    # Get the chapter type from planned types (index is 0-based, so subtract 1)
    chapter_type_index = current_chapter_number - 1
    if chapter_type_index < 0 or chapter_type_index >= len(state.planned_chapter_types):
        logger.error(
            f"Chapter type index {chapter_type_index} out of range for planned_chapter_types with length {len(state.planned_chapter_types)}"
        )
        # Use a default chapter type as fallback
        chapter_type = ChapterType.STORY
    else:
        chapter_type = state.planned_chapter_types[chapter_type_index]
        if not isinstance(chapter_type, ChapterType):
            chapter_type = ChapterType(chapter_type)

    # Start image generation - do this first to give more time for generation
    try:
        image_tasks = await start_image_generation_tasks(
            current_chapter_number, chapter_type, chapter_content, state
        )
        logger.info(
            f"Started {len(image_tasks)} image generation tasks for chapter {current_chapter_number}"
        )
    except Exception as e:
        logger.error(f"Error starting image generation tasks: {str(e)}")
        image_tasks = []  # Empty list as fallback

    # Stream chapter content
    await stream_text_content(content_to_stream, websocket)

    # Send complete chapter data with choices included
    await send_chapter_data(
        content_to_stream,
        chapter_content,
        chapter_type,
        current_chapter_number,
        sampled_question,
        state,
        websocket,
    )

    # Also send choices separately for backward compatibility
    await websocket.send_json(
        {
            "type": "choices",
            "choices": [
                {"text": choice.text, "id": choice.next_chapter}
                for choice in chapter_content.choices
            ],
        }
    )

    # Hide loader after streaming content, but before waiting for image tasks
    await websocket.send_json({"type": "hide_loader"})

    # If we have image tasks, wait for them to complete and send updates
    try:
        if image_tasks:
            await process_image_tasks(image_tasks, current_chapter_number, websocket)
            logger.info(f"Processed image tasks for chapter {current_chapter_number}")
        else:
            logger.warning(
                f"No image tasks available for chapter {current_chapter_number}, using fallback image"
            )
            await send_fallback_image(state, current_chapter_number, websocket)
    except Exception as e:
        logger.error(f"Error processing image tasks: {str(e)}")
        # Try to send a fallback image for the chapter
        await send_fallback_image(state, current_chapter_number, websocket)


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
