from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket
import asyncio
import logging
import re
from app.services.image_generation_service import ImageGenerationService
from app.models.story import (
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    StoryChoice,
    AdventureState,
)
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.adventure_state_manager import AdventureStateManager
from app.init_data import sample_question
import yaml

# Constants for streaming optimization
WORD_BATCH_SIZE = 1  # Reduced to stream word by word
WORD_DELAY = 0.02  # Delay between words
PARAGRAPH_DELAY = 0.1  # Delay between paragraphs

logger = logging.getLogger("story_app")
llm_service = LLMService()
chapter_manager = ChapterManager()
image_service = ImageGenerationService()


async def process_choice(
    state_manager: AdventureStateManager,
    choice_data: Dict[str, Any],
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process a user's choice and generate the next chapter.

    Args:
        state_manager: The state manager instance
        choice_data: The choice data from the client
        story_category: The story category
        lesson_topic: The lesson topic
        websocket: The WebSocket connection

    Returns:
        Tuple of (chapter_content, sampled_question, is_story_complete)
    """
    state = state_manager.get_current_state()
    if not state:
        return None, None, False

    # Extract choice information and debug state
    logger.debug(f"Raw choice_data: {choice_data}")
    if isinstance(choice_data, dict):
        chosen_path = choice_data.get("id") or choice_data.get("chosen_path", "")
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

    # Handle non-start choices
    if chosen_path != "start":
        logger.debug(f"Processing non-start choice: {chosen_path}")
        logger.debug(f"Current state chapters: {len(state.chapters)}")

        current_chapter_number = len(state.chapters) + 1
        logger.debug(f"Processing chapter {current_chapter_number}")
        chapter_type = state.planned_chapter_types[current_chapter_number - 1]
        if not isinstance(chapter_type, ChapterType):
            chapter_type = ChapterType(chapter_type)
        logger.debug(f"Next chapter type: {chapter_type}")

        previous_chapter = state.chapters[-1]
        logger.debug("\n=== DEBUG: Previous Chapter Info ===")
        logger.debug(f"Previous chapter number: {previous_chapter.chapter_number}")
        logger.debug(f"Previous chapter type: {previous_chapter.chapter_type}")
        logger.debug(
            f"Previous chapter has response: {previous_chapter.response is not None}"
        )
        if previous_chapter.response:
            logger.debug(
                f"Previous chapter response type: {type(previous_chapter.response)}"
            )
        logger.debug("===================================\n")

        if previous_chapter.chapter_type == ChapterType.LESSON:
            logger.debug("\n=== DEBUG: Processing Lesson Response ===")
            logger.debug(f"Previous chapter number: {previous_chapter.chapter_number}")
            logger.debug(
                f"Previous chapter has question: {previous_chapter.question is not None}"
            )
            logger.debug(f"Choice data: {choice_data}")

            try:
                # Create lesson response using the stored question data
                if previous_chapter.question:
                    correct_answer = next(
                        answer["text"]
                        for answer in previous_chapter.question["answers"]
                        if answer["is_correct"]
                    )
                    lesson_response = LessonResponse(
                        question=previous_chapter.question,
                        chosen_answer=choice_text,
                        is_correct=choice_text == correct_answer,
                    )
                    previous_chapter.response = lesson_response
                    logger.debug("\n=== DEBUG: Created Lesson Response ===")
                    logger.debug(f"Question: {previous_chapter.question['question']}")
                    logger.debug(f"Chosen answer: {choice_text}")
                    logger.debug(f"Correct answer: {correct_answer}")
                    logger.debug(f"Is correct: {choice_text == correct_answer}")
                    logger.debug("====================================\n")
                else:
                    logger.error("Previous chapter missing question data")
                    await websocket.send_text(
                        "An error occurred while processing your answer. Missing question data."
                    )
                    return None, None, False
            except Exception as e:
                logger.error(f"Error creating lesson response: {e}")
                await websocket.send_text(
                    "An error occurred while processing your answer. Please try again."
                )
                return None, None, False
        else:
            story_response = StoryResponse(
                chosen_path=chosen_path, choice_text=choice_text
            )
            previous_chapter.response = story_response
            logger.debug(f"Created story response: {story_response}")

            # Handle first chapter agency choice
            if (
                previous_chapter.chapter_number == 1
                and previous_chapter.chapter_type == ChapterType.STORY
            ):
                logger.debug("Processing first chapter agency choice")

                # Extract agency type and name from choice text
                agency_type = ""
                agency_name = ""

                # Determine agency type based on keywords in choice text
                choice_lower = choice_text.lower()
                if any(
                    word in choice_lower
                    for word in [
                        "craft",
                        "lantern",
                        "rope",
                        "amulet",
                        "map",
                        "watch",
                        "potion",
                    ]
                ):
                    agency_type = "item"
                    # Extract item name
                    item_patterns = [
                        r"luminous lantern",
                        r"sturdy rope",
                        r"mystical amulet",
                        r"weathered map",
                        r"pocket watch",
                        r"healing potion",
                    ]
                    for pattern in item_patterns:
                        if re.search(pattern, choice_lower, re.IGNORECASE):
                            agency_name = re.search(
                                pattern, choice_text, re.IGNORECASE
                            ).group(0)
                            break
                    if not agency_name:
                        # Generic extraction if specific patterns don't match
                        agency_name = re.search(
                            r"(?:a|the)\s+([^\s,\.]+(?:\s+[^\s,\.]+){0,2})",
                            choice_text,
                            re.IGNORECASE,
                        )
                        agency_name = (
                            agency_name.group(1) if agency_name else "magical item"
                        )

                elif any(
                    word in choice_lower
                    for word in [
                        "owl",
                        "fox",
                        "squirrel",
                        "deer",
                        "otter",
                        "turtle",
                        "companion",
                    ]
                ):
                    agency_type = "companion"
                    # Extract companion name
                    companion_patterns = [
                        r"wise owl",
                        r"brave fox",
                        r"clever squirrel",
                        r"gentle deer",
                        r"playful otter",
                        r"steadfast turtle",
                    ]
                    for pattern in companion_patterns:
                        if re.search(pattern, choice_lower, re.IGNORECASE):
                            agency_name = re.search(
                                pattern, choice_text, re.IGNORECASE
                            ).group(0)
                            break
                    if not agency_name:
                        # Generic extraction if specific patterns don't match
                        agency_name = re.search(
                            r"(?:a|the)\s+([^\s,\.]+(?:\s+[^\s,\.]+){0,2})",
                            choice_text,
                            re.IGNORECASE,
                        )
                        agency_name = (
                            agency_name.group(1) if agency_name else "animal companion"
                        )

                elif any(
                    word in choice_lower
                    for word in [
                        "healer",
                        "scholar",
                        "guardian",
                        "pathfinder",
                        "diplomat",
                        "craftsperson",
                        "role",
                    ]
                ):
                    agency_type = "role"
                    # Extract role name
                    role_patterns = [
                        r"healer",
                        r"scholar",
                        r"guardian",
                        r"pathfinder",
                        r"diplomat",
                        r"craftsperson",
                    ]
                    for pattern in role_patterns:
                        if re.search(pattern, choice_lower, re.IGNORECASE):
                            agency_name = re.search(
                                pattern, choice_text, re.IGNORECASE
                            ).group(0)
                            break
                    if not agency_name:
                        agency_name = "chosen role"

                elif any(
                    word in choice_lower
                    for word in [
                        "whisperer",
                        "master",
                        "storyteller",
                        "bender",
                        "walker",
                        "seer",
                        "ability",
                    ]
                ):
                    agency_type = "ability"
                    # Extract ability name
                    ability_patterns = [
                        r"animal whisperer",
                        r"puzzle master",
                        r"storyteller",
                        r"element bender",
                        r"dream walker",
                        r"pattern seer",
                    ]
                    for pattern in ability_patterns:
                        if re.search(pattern, choice_lower, re.IGNORECASE):
                            agency_name = re.search(
                                pattern, choice_text, re.IGNORECASE
                            ).group(0)
                            break
                    if not agency_name:
                        agency_name = "special ability"

                # If we couldn't determine the type, use a generic approach
                if not agency_type:
                    agency_type = "choice"
                    agency_name = "from Chapter 1"

                # Store agency choice in metadata
                state.metadata["agency"] = {
                    "type": agency_type,
                    "name": agency_name,
                    "description": choice_text,
                    "properties": {"strength": 1},
                    "growth_history": [],
                    "references": [],
                }

                logger.debug(f"Stored agency choice: {agency_type} - {agency_name}")

        state.current_chapter_id = chosen_path

    # Calculate new chapter number and update story phase
    new_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[new_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Update the storytelling phase based on the new chapter number
    state.current_storytelling_phase = ChapterManager.determine_story_phase(
        new_chapter_number, state.story_length
    )

    # Generate new chapter content
    chapter_content, sampled_question = await generate_chapter(
        story_category, lesson_topic, state
    )

    # Create and append new chapter
    try:
        new_chapter = ChapterData(
            chapter_number=len(state.chapters) + 1,
            content=re.sub(
                r"^Chapter\s+\d+:\s*", "", chapter_content.content, flags=re.MULTILINE
            ).strip(),
            chapter_type=chapter_type,
            response=None,
            chapter_content=chapter_content,
            question=sampled_question,
        )
        state_manager.append_new_chapter(new_chapter)
        logger.debug(f"Added new chapter {new_chapter.chapter_number}")
        logger.debug(f"Chapter type: {chapter_type}")
        logger.debug(f"Has question: {sampled_question is not None}")
    except ValueError as e:
        logger.error(f"Error adding chapter: {e}")
        await websocket.send_text(
            "An error occurred while processing your choice. Please try again."
        )
        return None, None, False

    # Check if story is complete - only when we've reached the final CONCLUSION chapter
    is_story_complete = (
        len(state.chapters) == state.story_length
        and state.chapters[-1].chapter_type == ChapterType.CONCLUSION
    )

    return chapter_content, sampled_question, is_story_complete


async def stream_and_send_chapter(
    websocket: WebSocket,
    chapter_content: ChapterContent,
    sampled_question: Optional[Dict[str, Any]],
    state: AdventureState,
) -> None:
    """Stream chapter content and send chapter data to the client.

    Args:
        websocket: The WebSocket connection
        chapter_content: The chapter content to stream
        sampled_question: The question data (if any)
        state: The current state
    """
    # Remove any "Chapter X:" prefix before streaming
    content_to_stream = re.sub(
        r"^Chapter\s+\d+:\s*", "", chapter_content.content, flags=re.MULTILINE
    ).strip()

    # Get chapter type for current chapter
    current_chapter_number = len(state.chapters)
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Start image generation for Chapter 1 agency choices
    image_tasks = []
    if current_chapter_number == 1 and chapter_type == ChapterType.STORY:
        logger.info("Starting image generation for Chapter 1 agency choices")

        # Attempt to extract original agency options from the prompt templates
        from app.services.llm.prompt_templates import get_agency_category

        # Get all possible agency categories and options for lookup
        agency_lookup = {}
        try:
            for _ in range(10):  # Try a few times to ensure we capture all categories
                category_name, formatted_options = get_agency_category()
                options_list = formatted_options.split("\n")
                for option in options_list:
                    if option.startswith("- "):
                        option = option[2:]  # Remove "- " prefix
                        # Create a simplified key for matching
                        key = re.sub(r"\s*\[.*?\]", "", option).lower()
                        # Store the original option with visual details
                        agency_lookup[key] = option
        except Exception as e:
            logger.error(f"Error building agency lookup: {e}")

        logger.debug(f"Built agency lookup with {len(agency_lookup)} entries")

        # Start async image generation for each choice
        for i, choice in enumerate(chapter_content.choices):
            # Try to find if this choice corresponds to an agency option
            # by looking for agency names in the choice text
            original_option = None
            choice_text = choice.text.lower()

            # Look for matches in our agency lookup
            for key, option in agency_lookup.items():
                # Extract the name part (before the first " - ")
                name_match = re.search(r"^([^-]+)", key)
                if name_match and name_match.group(1).strip() in choice_text:
                    original_option = option
                    logger.debug(
                        f"Found matching agency option for choice {i + 1}: {original_option}"
                    )
                    break

            # Use the original option with visual details if found, otherwise use the choice text
            if original_option:
                prompt = image_service.enhance_prompt(original_option, state)
                logger.debug(
                    f"Using original agency option for image: {original_option}"
                )
            else:
                prompt = image_service.enhance_prompt(choice.text, state)
                logger.debug(f"No match found, using choice text: {choice.text}")

            image_tasks.append(
                (i, asyncio.create_task(image_service.generate_image_async(prompt)))
            )
            logger.debug(
                f"Started image generation task for choice {i + 1}: {choice.text}"
            )

    # Split content into paragraphs and stream
    paragraphs = [p.strip() for p in content_to_stream.split("\n\n") if p.strip()]

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

        # Stream the paragraph word by word
        words = paragraph.split()
        for word in words:
            await websocket.send_text(word + " ")
            await asyncio.sleep(WORD_DELAY)
        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)

    # Send complete chapter data with choices included
    chapter_data = {
        "type": "chapter_update",
        "state": {
            "current_chapter_id": state.current_chapter_id,
            "current_chapter": {
                "chapter_number": current_chapter_number,
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
        },
    }
    logger.debug("\n=== DEBUG: Chapter Update Message ===")
    logger.debug(f"Chapter number: {current_chapter_number}")
    logger.debug(f"Chapter type: {chapter_type.value}")
    logger.debug(f"Has question: {sampled_question is not None}")
    logger.debug("===================================\n")
    await websocket.send_json(chapter_data)

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

    # If we have image tasks, wait for them to complete and send updates
    if image_tasks:
        logger.info(
            f"Waiting for {len(image_tasks)} image generation tasks to complete"
        )
        for i, task in image_tasks:
            try:
                image_data = await task
                if image_data:
                    logger.info(f"Image generated for choice {i + 1}, sending update")
                    # Send image update for this choice
                    await websocket.send_json(
                        {
                            "type": "choice_image_update",
                            "choice_index": i,
                            "image_data": image_data,
                        }
                    )
                else:
                    logger.warning(f"No image data generated for choice {i + 1}")
                    # Could implement a fallback here if needed
                    # For example, use a placeholder image or skip image display
            except Exception as e:
                logger.error(
                    f"Error waiting for image generation task {i + 1}: {str(e)}"
                )
                # Log the error but continue processing other tasks


async def send_story_complete(
    websocket: WebSocket,
    state: AdventureState,
) -> None:
    """Send story completion data to the client.

    Args:
        websocket: The WebSocket connection
        state: The current state
    """
    # Get the final chapter (which should be CONCLUSION type)
    final_chapter = state.chapters[-1]

    # Stream the content first
    content_to_stream = final_chapter.content
    paragraphs = [p.strip() for p in content_to_stream.split("\n\n") if p.strip()]

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

        # Stream the paragraph word by word
        words = paragraph.split()
        for i in range(0, len(words), WORD_BATCH_SIZE):
            batch = " ".join(words[i : i + WORD_BATCH_SIZE])
            await websocket.send_text(batch + " ")
            await asyncio.sleep(WORD_DELAY)
        await websocket.send_text("\n\n")
        await asyncio.sleep(PARAGRAPH_DELAY)

    # Then send the completion message with stats
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
            },
        }
    )


async def generate_chapter(
    story_category: str,
    lesson_topic: str,
    state: AdventureState,
) -> Tuple[ChapterContent, Optional[dict]]:
    """Generate a complete chapter with content and choices.

    Args:
        story_category: The story category
        lesson_topic: The lesson topic
        state: The current state

    Returns:
        Tuple of (ChapterContent, Optional[dict])
    """
    # Load story configuration
    with open("app/data/new_stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
    story_config = story_data["story_categories"][story_category]

    # Get chapter type
    current_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Initialize variables
    story_content = ""
    question = None
    previous_lessons = []

    # Get previous lessons from chapter history
    previous_lessons = [
        LessonResponse(
            question=chapter.response.question,
            chosen_answer=chapter.response.chosen_answer,
            is_correct=chapter.response.is_correct,
        )
        for chapter in state.chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response
    ]

    logger.debug("\n=== DEBUG: Previous Lessons Collection ===")
    logger.debug(f"Total chapters: {len(state.chapters)}")
    logger.debug(f"Current chapter number: {current_chapter_number}")
    logger.debug(f"Current chapter type: {chapter_type}")
    logger.debug(f"Number of previous lessons: {len(previous_lessons)}")

    if previous_lessons:
        logger.debug("\nLesson details:")
        for i, pl in enumerate(previous_lessons, 1):
            logger.debug(f"Lesson {i}:")
            logger.debug(f"Question: {pl.question['question']}")
            logger.debug(f"Chosen Answer: {pl.chosen_answer}")
            logger.debug(f"Is Correct: {pl.is_correct}")
    else:
        logger.debug("No previous lessons found")
    logger.debug("=========================================\n")

    # Load new question if at lesson chapter
    if chapter_type == ChapterType.LESSON:
        try:
            used_questions = [
                chapter.response.question["question"]
                for chapter in state.chapters
                if chapter.chapter_type == ChapterType.LESSON and chapter.response
            ]
            question = sample_question(lesson_topic, exclude_questions=used_questions)
            logger.debug(f"DEBUG: Selected question: {question['question']}")
            logger.debug(f"DEBUG: Answers: {question['answers']}")
        except ValueError as e:
            logger.error(f"Error sampling question: {e}")
            raise

    # Generate story content
    try:
        async for chunk in llm_service.generate_chapter_stream(
            story_config,
            state,
            question,
            previous_lessons,
        ):
            story_content += chunk

        # Check for dialogue formatting issues in the generated content
        if re.match(
            r"^(chirped|said|whispered|shouted|called|murmured|exclaimed|replied|asked|answered|responded)\b",
            story_content.strip(),
        ):
            logger.warning(
                "Generated content starts with dialogue verb - possible missing character name"
            )
            # Log the issue but continue processing normally

    except Exception as e:
        logger.error("\n=== ERROR: LLM Request Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("===============================\n")
        raise

    # Extract choices based on chapter type
    if chapter_type == ChapterType.LESSON and question:
        story_choices = []
        for answer in question["answers"]:
            story_choices.append(
                StoryChoice(
                    text=answer["text"],
                    next_chapter="correct"
                    if answer["is_correct"]
                    else f"wrong{len(story_choices) + 1}",
                )
            )
    elif chapter_type == ChapterType.STORY or chapter_type == ChapterType.REFLECT:
        # Both STORY and REFLECT chapters use the same choice extraction logic
        logger.debug(f"Extracting choices for {chapter_type.value} chapter")

        # Add more detailed logging for REFLECT chapters
        if chapter_type == ChapterType.REFLECT:
            logger.debug("Processing REFLECT chapter choices")
            logger.debug(f"Content length: {len(story_content)}")
            # Log the last 200 characters to see if <CHOICES> section is present
            logger.debug(
                f"Content tail: {story_content[-200:] if len(story_content) > 200 else story_content}"
            )
        try:
            # First extract the choices section
            choices_match = re.search(
                r"<CHOICES>\s*(.*?)\s*</CHOICES>",
                story_content,
                re.DOTALL | re.IGNORECASE,
            )

            if not choices_match:
                logger.error(
                    "Could not find choice markers in story content. Raw content:"
                )
                logger.error(story_content)
                raise ValueError("Could not find choice markers in story content")

            # Extract choices text and clean up story content
            choices_text = choices_match.group(1).strip()
            story_content = story_content[: choices_match.start()].strip()
            # Remove any "Chapter X:" prefix, including any whitespace after it
            story_content = re.sub(
                r"^Chapter\s+\d+:\s*", "", story_content, flags=re.MULTILINE
            ).strip()

            # Initialize choices array
            choices = []

            # Try multi-line format first (within choices section)
            choice_pattern = r"Choice\s*([ABC])\s*:\s*([^\n]+)"
            matches = re.finditer(
                choice_pattern, choices_text, re.IGNORECASE | re.MULTILINE
            )
            for match in matches:
                choices.append(match.group(2).strip())

            # If no matches found, try single-line format (still within choices section)
            if not choices:
                single_line_pattern = (
                    r"Choice\s*[ABC]\s*:\s*([^.]+(?:\.\s*(?=Choice\s*[ABC]\s*:|$))?)"
                )
                matches = re.finditer(single_line_pattern, choices_text, re.IGNORECASE)
                for match in matches:
                    choices.append(match.group(1).strip())

            if not choices:
                logger.error(f"No choices found in choices text. Raw choices text:")
                logger.error(choices_text)
                raise ValueError("No choices found in story content")

            if len(choices) != 3:
                logger.warning(
                    f"Expected 3 choices but found {len(choices)}. Raw choices text:"
                )
                logger.warning(choices_text)
                # If we found at least one choice, use what we have rather than failing
                if choices:
                    logger.info("Proceeding with available choices")
                else:
                    raise ValueError("Must have at least one valid choice")

            story_choices = [
                StoryChoice(
                    text=choice_text,
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i, choice_text in enumerate(choices)
            ]
        except Exception as e:
            logger.error(f"Error parsing choices: {e}")
            story_choices = [
                StoryChoice(
                    text=f"Continue with option {i + 1}",
                    next_chapter=f"chapter_{current_chapter_number}_{i}",
                )
                for i in range(3)
            ]
    else:  # CONCLUSION chapter
        story_choices = []  # No choices for conclusion chapters

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_chapter: {choice.next_chapter})")
    logger.debug("========================\n")

    return ChapterContent(content=story_content, choices=story_choices), question
