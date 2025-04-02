from typing import Dict, Optional, List, Tuple, Any
import logging
import asyncio
import re

from app.models.story import ChapterType, ChapterContent, AdventureState, StoryChoice
from app.services.image_generation_service import ImageGenerationService
from app.services.chapter_manager import ChapterManager

logger = logging.getLogger("story_app")
image_service = ImageGenerationService()
chapter_manager = ChapterManager()


async def start_image_generation_tasks(
    current_chapter_number: int,
    chapter_type: ChapterType,
    chapter_content: ChapterContent,
    state: AdventureState,
) -> List[Tuple[Any, asyncio.Task]]:
    """Start image generation tasks for the chapter."""
    image_tasks = []

    # Validate chapter number
    if current_chapter_number <= 0:
        logger.error(f"Invalid chapter number: {current_chapter_number}, must be positive")
        current_chapter_number = 1  # Set to 1 as a fallback

    # For Chapter 1, generate images for agency choices
    if current_chapter_number == 1 and chapter_type == ChapterType.STORY:
        image_tasks = await generate_agency_images(chapter_content, state)
    # For chapters after the first, generate a single image based on current chapter content
    elif current_chapter_number > 1:
        image_tasks = await generate_chapter_image(current_chapter_number, state)
    else:
        logger.warning(f"No image tasks started for chapter {current_chapter_number}, type: {chapter_type}")

    logger.info(f"Started {len(image_tasks)} image tasks for chapter {current_chapter_number}")
    return image_tasks


async def generate_agency_images(
    chapter_content: ChapterContent, state: AdventureState
) -> List[Tuple[int, asyncio.Task]]:
    """Generate images for agency choices in Chapter 1.

    This function handles the special case of Chapter 1 agency choice images.
    For agency choices, we focus *only* on the agency item/companion/ability/profession itself,
    using its visual description plus atmospheric sensory detail.

    Args:
        chapter_content: The chapter content with choices
        state: The current adventure state

    Returns:
        A list of tuples with choice indexes and image generation tasks
    """
    logger.info("Starting image generation for Chapter 1 agency choices")
    image_tasks = []

    # Get direct access to all agency options from prompt_templates
    agency_lookup = build_agency_lookup()

    if not chapter_content.choices:
        logger.error("No choices found in chapter content")
        return image_tasks

    # Retrieve the story visual sensory detail
    story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")
    
    # Start async image generation for each choice
    for i, choice in enumerate(chapter_content.choices):
        try:
            # Find matching agency option with visual details
            original_option = find_matching_agency_option(choice.text, agency_lookup)

            # Generate the image prompt
            if original_option:
                # Extract visual details from the original option (text in square brackets)
                visual_match = re.search(r"\[(.*?)\]", original_option)
                visual_details = ""
                if visual_match:
                    visual_details = visual_match.group(1)

                # Extract the agency name (text before bracket)
                agency_name = original_option.split("[")[0].strip()

                # Construct the focused prompt
                prompt = f"Fantasy illustration of {agency_name} - {visual_details}. The background has subtle elements of {story_visual_sensory_detail}"
            else:
                # If no match found, use the choice text directly
                prompt = f"Fantasy illustration of {choice.text}. The background has subtle hints of: {story_visual_sensory_detail}"

            # Create the image generation task - no need to log prompts here as they'll be logged in the image service
            image_tasks.append(
                (i, asyncio.create_task(image_service.generate_image_async(prompt)))
            )
            logger.info(f"Started image generation task for choice {i + 1}")
        except Exception as e:
            logger.error(f"Error generating image for choice {i + 1}: {str(e)}")
            continue

    return image_tasks


def build_agency_lookup() -> Dict[str, str]:
    """Build a lookup dictionary of agency options."""
    agency_lookup = {}
    try:
        # Access the categories dictionary directly from prompt_templates
        from app.services.llm.prompt_templates import categories

        # Build a complete lookup of all agency options
        for category_name, options in categories.items():
            for option in options:
                # Extract the name (before the first '[')
                name = option.split("[")[0].strip()
                # Store the full option with visual details
                agency_lookup[name.lower()] = option

                # Also store variations to improve matching
                # For example, "Brave Fox" should match "Fox" as well
                if " " in name:
                    parts = name.split(" ")
                    for part in parts:
                        if (
                            len(part) > 3
                        ):  # Only use meaningful parts (avoid "the", "of", etc.)
                            agency_lookup[part.lower()] = option
    except Exception as e:
        logger.error(f"Error building agency lookup: {e}")
        # Fallback to the original method if direct access fails
        try:
            from app.services.llm.prompt_templates import get_agency_category

            for _ in range(10):  # Try a few times to ensure we capture all categories
                category_name, formatted_options, _ = get_agency_category()
                options_list = formatted_options.split("\n")
                for option in options_list:
                    if option.startswith("- "):
                        option = option[2:]  # Remove "- " prefix
                        # Create a simplified key for matching
                        key = re.sub(r"\s*\[.*?\]", "", option).lower()
                        # Store the original option with visual details
                        agency_lookup[key] = option
        except Exception as e2:
            logger.error(f"Error in fallback agency lookup: {e2}")

    return agency_lookup


def find_matching_agency_option(
    choice_text: str, agency_lookup: Dict[str, str]
) -> Optional[str]:
    """Find a matching agency option for the given choice text."""
    try:
        from app.services.llm.prompt_templates import categories

        # Extract the core name from the choice text
        clean_text = choice_text.lower()

        # Try to find a matching agency option in categories
        for category_options in categories.values():
            for option in category_options:
                option_name = option.split("[")[0].strip().lower()

                # Check if option name is in the choice text
                if option_name in clean_text:
                    return option

        # If no match found, try using the agency_lookup as fallback
        if agency_lookup:
            # Try to match with any key in the lookup
            for key, option in agency_lookup.items():
                if key in clean_text:
                    return option
    except Exception as e:
        logger.error(f"Error finding agency option: {e}")

    return None


async def generate_chapter_image(
    current_chapter_number: int, state: AdventureState
) -> List[Tuple[str, asyncio.Task]]:
    """Generate an image for the current chapter using the two-step prompt generation process.

    This function uses a standardized approach for all image generation:
    1. For all chapters, use the chapter_manager.generate_image_scene method
    2. This method uses the IMAGE_SCENE_PROMPT template to generate a scene description
    3. Pass this scene description to image_service.synthesize_image_prompt along with protagonist and agency details
    4. Generate the image using the synthesized prompt

    For Chapter 1, if character_visuals is empty, it will attempt to extract character descriptions
    from the chapter content to ensure visual consistency.

    Args:
        current_chapter_number: The chapter number
        state: The current adventure state

    Returns:
        A list of tuples containing the image identifier and task
    """
    logger.info(f"Starting image generation for Chapter {current_chapter_number}")
    image_tasks = []

    # Skip image generation for chapter 0 (invalid chapter number)
    if current_chapter_number <= 0:
        logger.error(f"Invalid chapter number {current_chapter_number}, cannot generate image")
        return image_tasks

    try:
        # We need a chapter content to generate an image
        if len(state.chapters) == 0:
            # Special case for first chapter - use story metadata
            if current_chapter_number == 1:
                # Create a scene description from story metadata
                story_category = getattr(state, "storyCategory", "")
                scene_description = f"Adventure beginning in a wondrous {story_category} setting with colorful characters and magical elements"

                # Get protagonist description
                protagonist_description = getattr(state, "protagonist_description", "A young adventurer")

                # Get agency details (empty for first chapter)
                agency_details = {}

                # Get story visual sensory detail
                story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")

                # Get character visuals if available
                character_visuals = getattr(state, "character_visuals", {})

                prompt = await image_service.synthesize_image_prompt(
                    scene_description,
                    protagonist_description,
                    agency_details,
                    story_visual_sensory_detail,
                    character_visuals,
                )

                # Create the image generation task
                image_tasks.append(
                    (
                        "chapter",
                        asyncio.create_task(image_service.generate_image_async(prompt)),
                    )
                )
                return image_tasks

            # For other chapters with no content, we need content to generate an image
            logger.error("No chapters available for image generation")
            return image_tasks

        # Get the most relevant chapter content - always use the most recently added chapter
        current_chapter = state.chapters[-1]
        current_content = current_chapter.content

        if not current_content or len(current_content.strip()) == 0:
            logger.error("Chapter has no content, cannot generate image")
            return image_tasks

        try:
            # Generate a description of the most visually striking moment
            image_scene = await chapter_manager.generate_image_scene(current_content)
            
            # Get protagonist description
            protagonist_description = getattr(state, "protagonist_description", "A young adventurer")

            # Get agency details
            agency_details = state.metadata.get("agency", {})

            # Get story visual sensory detail
            story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")

            # Get character visuals if available
            character_visuals = getattr(state, "character_visuals", {})
            
            # If Chapter 1 is lacking character visuals, attempt to extract them from the chapter content
            if current_chapter_number == 1 and not character_visuals:
                # Import the function dynamically to avoid circular imports
                from app.services.websocket.choice_processor import diagnose_character_visuals
                
                try:
                    # Use the diagnostic function to extract character visuals
                    extracted_visuals = await diagnose_character_visuals(current_content, {})
                    
                    if extracted_visuals:
                        logger.info(f"Extracted {len(extracted_visuals)} character visuals from Chapter 1")
                        character_visuals = extracted_visuals
                        
                        # Update the state directly for future use
                        state.character_visuals = extracted_visuals
                except Exception as extraction_error:
                    logger.error(f"Error extracting character visuals: {extraction_error}")

            # Synthesize the image prompt
            prompt = await image_service.synthesize_image_prompt(
                image_scene,
                protagonist_description,
                agency_details,
                story_visual_sensory_detail,
                character_visuals,
            )

            # Create the image generation task
            image_tasks.append(
                (
                    "chapter",
                    asyncio.create_task(image_service.generate_image_async(prompt)),
                )
            )

        except Exception as scene_error:
            logger.error(f"Error generating image scene: {str(scene_error)}")
            # Use a fallback approach
            # Extract a short preview of the chapter content as a fallback
            content_preview = current_content[:150].replace("\n", " ").strip()
            image_scene = f"A scene from the story showing {content_preview}..."

            # Get protagonist description
            protagonist_description = getattr(state, "protagonist_description", "A young adventurer")

            # Get agency details
            agency_details = state.metadata.get("agency", {})

            # Get story visual sensory detail
            story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")

            # Get character visuals if available
            character_visuals = getattr(state, "character_visuals", {})

            prompt = await image_service.synthesize_image_prompt(
                image_scene,
                protagonist_description,
                agency_details,
                story_visual_sensory_detail,
                character_visuals,
            )

            # Create the image generation task
            image_tasks.append(
                (
                    "chapter",
                    asyncio.create_task(image_service.generate_image_async(prompt)),
                )
            )
            logger.info(f"Using fallback image generation with scene summary")

    except Exception as e:
        logger.error(f"Error generating chapter image: {str(e)}")
        # Log stack trace for debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

    return image_tasks


async def process_image_tasks(
    image_tasks: List[Tuple[Any, asyncio.Task]],
    current_chapter_number: int,
    websocket: Any,
) -> None:
    """Process completed image generation tasks."""
    if not image_tasks:
        logger.warning(f"No image tasks to process for chapter {current_chapter_number}")
        return

    logger.info(f"Chapter {current_chapter_number}: Waiting for {len(image_tasks)} image generation tasks to complete")

    # Set a timeout for all image tasks
    timeout_seconds = 30  # Adjust this value as needed

    for identifier, task in image_tasks:
        try:
            # Use wait_for with timeout to prevent hanging indefinitely
            try:
                image_data = await asyncio.wait_for(task, timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Image generation for {identifier} timed out after {timeout_seconds} seconds")
                continue

            if not image_data:
                logger.warning(f"No image data generated for {identifier}")
                continue

            # For Chapter 1 agency choices
            if isinstance(identifier, int):
                # Send image update for this choice
                await websocket.send_json(
                    {
                        "type": "choice_image_update",
                        "choice_index": identifier,
                        "image_data": image_data,
                    }
                )
                logger.info(f"Sent image update for choice {identifier + 1}")

            # For chapter images (chapters after the first)
            elif identifier == "chapter":
                # Send image update for the chapter
                await websocket.send_json(
                    {
                        "type": "chapter_image_update",
                        "chapter_number": current_chapter_number,
                        "image_data": image_data,
                    }
                )
                logger.info(f"Sent image update for chapter {current_chapter_number}")

        except Exception as e:
            logger.error(f"Error processing image task for {identifier}: {str(e)}")
            # Log the stack trace for debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
