from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket
import asyncio
import logging
import re
from app.services.image_generation_service import ImageGenerationService
from app.models.story import (
    ChapterType,
    ChapterContent,
    ChapterContentValidator,
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
from app.data.story_loader import StoryLoader

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

    # Check for special "reveal_summary" choice
    if chosen_path == "reveal_summary":
        logger.info("Processing reveal_summary choice")
        logger.info(f"Current state has {len(state.chapters)} chapters")
        logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")

        # Get the CONCLUSION chapter
        if state.chapters and state.chapters[-1].chapter_type == ChapterType.CONCLUSION:
            conclusion_chapter = state.chapters[-1]
            logger.info(
                f"Found CONCLUSION chapter: {conclusion_chapter.chapter_number}"
            )
            logger.info(
                f"CONCLUSION chapter content length: {len(conclusion_chapter.content)}"
            )

            # Generate summary for the CONCLUSION chapter
            try:
                logger.info(f"Generating summary for CONCLUSION chapter")
                summary_result = await chapter_manager.generate_chapter_summary(
                    conclusion_chapter.content,
                    "End of story",  # Placeholder for chosen_choice
                    "",  # Empty choice_context
                )

                # Extract title and summary from the result
                title = summary_result.get("title", "Chapter Summary")
                summary_text = summary_result.get("summary", "Summary not available")

                logger.info(
                    f"Generated CONCLUSION chapter summary: {summary_text[:100]}..."
                )

                # Store the summary
                if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
                    logger.info(
                        f"Adding placeholder summaries up to chapter {conclusion_chapter.chapter_number - 1}"
                    )
                    while (
                        len(state.chapter_summaries)
                        < conclusion_chapter.chapter_number - 1
                    ):
                        state.chapter_summaries.append("Chapter summary not available")
                        # Also add placeholder titles
                        if hasattr(state, "summary_chapter_titles"):
                            state.summary_chapter_titles.append(
                                f"Chapter {len(state.summary_chapter_titles) + 1}"
                            )

                    # Add the new summary and title
                    state.chapter_summaries.append(summary_text)
                    # Add the title if the field exists
                    if hasattr(state, "summary_chapter_titles"):
                        state.summary_chapter_titles.append(title)
                else:
                    logger.info(
                        f"Updating existing summary at index {conclusion_chapter.chapter_number - 1}"
                    )
                    state.chapter_summaries[conclusion_chapter.chapter_number - 1] = (
                        summary_text
                    )
                    # Update the title if the field exists
                    if hasattr(state, "summary_chapter_titles"):
                        # Ensure the list is long enough
                        while (
                            len(state.summary_chapter_titles)
                            < conclusion_chapter.chapter_number
                        ):
                            state.summary_chapter_titles.append(
                                f"Chapter {len(state.summary_chapter_titles) + 1}"
                            )
                        state.summary_chapter_titles[
                            conclusion_chapter.chapter_number - 1
                        ] = title

                logger.info(
                    f"Stored summary for chapter {conclusion_chapter.chapter_number}: {summary_text}"
                )
                if hasattr(state, "summary_chapter_titles"):
                    logger.info(
                        f"Stored title for chapter {conclusion_chapter.chapter_number}: {title}"
                    )
            except Exception as e:
                logger.error(
                    f"Error generating chapter summary: {str(e)}", exc_info=True
                )
                if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
                    logger.warning(
                        f"Using fallback summary for chapter {conclusion_chapter.chapter_number}"
                    )
                    state.chapter_summaries.append("Chapter summary not available")

        # Create and generate the SUMMARY chapter
        summary_chapter = chapter_manager.create_summary_chapter(state)
        summary_content = await generate_summary_content(state)
        summary_chapter.content = summary_content
        summary_chapter.chapter_content.content = summary_content

        # Add the SUMMARY chapter to the state
        state_manager.append_new_chapter(summary_chapter)

        # Stream the summary content to the client
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

        # Send the complete summary data
        await websocket.send_json(
            {
                "type": "summary_complete",
                "state": {
                    "current_chapter_id": state.current_chapter_id,
                    "current_chapter": {
                        "chapter_number": summary_chapter.chapter_number,
                        "content": summary_content,
                        "chapter_type": ChapterType.SUMMARY.value,
                    },
                    "stats": {
                        "total_lessons": state.total_lessons,
                        "correct_lesson_answers": state.correct_lesson_answers,
                        "completion_percentage": round(
                            (state.correct_lesson_answers / state.total_lessons * 100)
                            if state.total_lessons > 0
                            else 0
                        ),
                    },
                    "chapter_summaries": state.chapter_summaries,
                },
            }
        )

        return None, None, False

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
                    
                    # Store in lesson_questions array for summary chapter
                    if not hasattr(state, "lesson_questions"):
                        state.lesson_questions = []
                    
                    # Create question object for summary display
                    question_obj = {
                        "question": previous_chapter.question.get("question", "Unknown question"),
                        "answers": previous_chapter.question.get("answers", []),
                        "chosen_answer": choice_text,
                        "is_correct": choice_text == correct_answer,
                        "explanation": previous_chapter.question.get("explanation", ""),
                        "correct_answer": correct_answer
                    }
                    
                    # Append to state's lesson_questions
                    state.lesson_questions.append(question_obj)
                    logger.info(f"Added question to lesson_questions array: {question_obj['question']}")
                    
                    logger.debug("\n=== DEBUG: Created Lesson Response ===")
                    logger.debug(f"Question: {previous_chapter.question['question']}")
                    logger.debug(f"Chosen answer: {choice_text}")
                    logger.debug(f"Correct answer: {correct_answer}")
                    logger.debug(f"Is correct: {choice_text == correct_answer}")
                    logger.debug(f"Questions in lesson_questions: {len(state.lesson_questions)}")
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

                # Simplify agency choice handling - just store the choice text
                # without complex categorization

                # Store agency choice in metadata
                state.metadata["agency"] = {
                    "type": "choice",
                    "name": "from Chapter 1",
                    "description": choice_text,
                    "properties": {"strength": 1},
                    "growth_history": [],
                    "references": [],
                }

                logger.debug(f"Stored agency choice from Chapter 1: {choice_text}")

        # Generate a chapter summary for the previous chapter
        try:
            logger.info(
                f"Generating summary for chapter {previous_chapter.chapter_number}"
            )

            # Extract the choice text and context from the response
            choice_text = ""
            choice_context = ""

            if isinstance(previous_chapter.response, StoryResponse):
                choice_text = previous_chapter.response.choice_text
                # No additional context needed for STORY chapters
            elif isinstance(previous_chapter.response, LessonResponse):
                choice_text = previous_chapter.response.chosen_answer
                choice_context = (
                    " (Correct answer)"
                    if previous_chapter.response.is_correct
                    else " (Incorrect answer)"
                )

            summary_result = await chapter_manager.generate_chapter_summary(
                previous_chapter.content, choice_text, choice_context
            )

            # Extract title and summary from the result
            title = summary_result.get("title", "Chapter Summary")
            summary_text = summary_result.get("summary", "Summary not available")

            # Store the chapter summary and title in the state
            if len(state.chapter_summaries) < previous_chapter.chapter_number:
                # If this is the first summary, we might need to add placeholders for previous chapters
                while (
                    len(state.chapter_summaries) < previous_chapter.chapter_number - 1
                ):
                    state.chapter_summaries.append("Chapter summary not available")
                    # Also add placeholder titles
                    if hasattr(state, "summary_chapter_titles"):
                        state.summary_chapter_titles.append(
                            f"Chapter {len(state.summary_chapter_titles) + 1}"
                        )

                # Add the new summary and title
                state.chapter_summaries.append(summary_text)
                # Add the title if the field exists
                if hasattr(state, "summary_chapter_titles"):
                    state.summary_chapter_titles.append(title)
            else:
                # Replace the summary at the correct index
                state.chapter_summaries[previous_chapter.chapter_number - 1] = (
                    summary_text
                )
                # Replace the title if the field exists
                if hasattr(state, "summary_chapter_titles"):
                    # Ensure the list is long enough
                    while (
                        len(state.summary_chapter_titles)
                        < previous_chapter.chapter_number
                    ):
                        state.summary_chapter_titles.append(
                            f"Chapter {len(state.summary_chapter_titles) + 1}"
                        )
                    state.summary_chapter_titles[
                        previous_chapter.chapter_number - 1
                    ] = title

            logger.info(
                f"Stored summary for chapter {previous_chapter.chapter_number}: {summary_text}"
            )
            if hasattr(state, "summary_chapter_titles"):
                logger.info(
                    f"Stored title for chapter {previous_chapter.chapter_number}: {title}"
                )
        except Exception as e:
            logger.error(f"Error generating chapter summary: {str(e)}")
            # Don't fail the whole process if summary generation fails
            if len(state.chapter_summaries) < previous_chapter.chapter_number:
                state.chapter_summaries.append("Chapter summary not available")

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
        # Use the Pydantic validator to clean the content
        try:
            validated_content = ChapterContentValidator(
                content=chapter_content.content
            ).content
            if validated_content != chapter_content.content:
                logger.info(
                    "Content was cleaned by ChapterContentValidator in process_choice"
                )
        except Exception as e:
            logger.error(f"Error in Pydantic validation in process_choice: {e}")
            # Fallback to regex if Pydantic validation fails
            validated_content = re.sub(
                r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
                "",
                chapter_content.content,
                flags=re.IGNORECASE,
            )
            logger.debug("Fallback to regex cleaning in process_choice")

        new_chapter = ChapterData(
            chapter_number=len(state.chapters) + 1,
            content=validated_content.strip(),
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
    # Use the Pydantic validator to clean the content before streaming
    try:
        content_to_stream = ChapterContentValidator(
            content=chapter_content.content
        ).content
        if content_to_stream != chapter_content.content:
            logger.info(
                "Content was cleaned by ChapterContentValidator in stream_and_send_chapter"
            )
    except Exception as e:
        logger.error(f"Error in Pydantic validation in stream_and_send_chapter: {e}")
        # Fallback to regex if Pydantic validation fails
        content_to_stream = re.sub(
            r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
            "",
            chapter_content.content,
            flags=re.IGNORECASE,
        )
        logger.debug("Fallback to regex cleaning in stream_and_send_chapter")

    content_to_stream = content_to_stream.strip()

    # Get chapter type for current chapter
    current_chapter_number = len(state.chapters)
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Start image generation
    image_tasks = []

    # For Chapter 1, generate images for agency choices
    if current_chapter_number == 1 and chapter_type == ChapterType.STORY:
        logger.info("Starting image generation for Chapter 1 agency choices")

        # Get direct access to all agency options from prompt_templates
        from app.services.llm.prompt_templates import get_agency_category

        # Create a comprehensive dictionary of all agency options
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
                for _ in range(
                    10
                ):  # Try a few times to ensure we capture all categories
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

        logger.debug(f"Built agency lookup with {len(agency_lookup)} entries")

        # Start async image generation for each choice
        for i, choice in enumerate(chapter_content.choices):
            # Simplified agency option extraction
            original_option = None

            try:
                from app.services.llm.prompt_templates import categories

                # Extract the core name from the choice text
                choice_text = choice.text
                clean_text = choice_text.lower()

                # Try to find a matching agency option in categories
                for category_options in categories.values():
                    for option in category_options:
                        option_name = option.split("[")[0].strip().lower()

                        # Check if option name is in the choice text
                        if option_name in clean_text:
                            original_option = option
                            logger.debug(f"Found matching agency option: {option_name}")
                            break

                    if original_option:
                        break

                # If no match found, try using the agency_lookup as fallback
                if not original_option and agency_lookup:
                    # Try to match with any key in the lookup
                    for key, option in agency_lookup.items():
                        if key in clean_text:
                            original_option = option
                            logger.debug(f"Found match in agency_lookup: {key}")
                            break
            except Exception as e:
                logger.error(f"Error finding agency option: {e}")

            # Generate the image prompt
            if original_option:
                # Pass the entire original option with visual details
                prompt = image_service.enhance_prompt(original_option, state)
                logger.debug(f"Using original agency option: {original_option}")
            else:
                # If no match found, use the choice text directly
                prompt = image_service.enhance_prompt(choice.text, state)
                logger.debug(f"Using choice text directly: {choice.text}")

            image_tasks.append(
                (i, asyncio.create_task(image_service.generate_image_async(prompt)))
            )
            logger.debug(
                f"Started image generation task for choice {i + 1}: {choice.text}"
            )
    # For chapters after the first, generate a single image based on previous chapter
    elif current_chapter_number > 1:
        logger.info(f"Starting image generation for Chapter {current_chapter_number}")

        try:
            # Get the current chapter's content (most recently added chapter)
            current_chapter = state.chapters[-1]  # The most recently added chapter
            current_content = current_chapter.content

            # Generate a description of the most visually striking moment from the chapter
            image_scene = await chapter_manager.generate_image_scene(current_content)

            logger.debug(
                f"Image scene before passing to enhance_prompt: '{image_scene}'"
            )

            # Create the image prompt using the image scene
            prompt = image_service.enhance_prompt(
                "", state, chapter_summary=image_scene
            )

            # Start the image generation task
            image_tasks.append(
                (
                    "chapter",
                    asyncio.create_task(image_service.generate_image_async(prompt)),
                )
            )
            logger.debug(
                f"Started image generation for chapter {current_chapter_number} with image scene: {image_scene}"
            )
        except Exception as e:
            logger.error(f"Error generating chapter image: {str(e)}")

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
            # Include chapter_summaries in the response for simulation logging
            "chapter_summaries": state.chapter_summaries,
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

    # Hide loader after streaming content, but before waiting for image tasks
    await websocket.send_json({"type": "hide_loader"})

    # If we have image tasks, wait for them to complete and send updates
    if image_tasks:
        logger.info(
            f"Chapter {current_chapter_number}: Waiting for {len(image_tasks)} image generation tasks to complete"
        )
        for identifier, task in image_tasks:
            try:
                logger.info(f"Awaiting image generation task for {identifier}...")
                image_data = await task
                if image_data:
                    # For Chapter 1 agency choices
                    if isinstance(identifier, int):
                        logger.info(
                            f"Image generated for choice {identifier + 1}, sending update"
                        )
                        # Send image update for this choice
                        await websocket.send_json(
                            {
                                "type": "choice_image_update",
                                "choice_index": identifier,
                                "image_data": image_data,
                            }
                        )
                    # For chapter images (chapters after the first)
                    elif identifier == "chapter":
                        logger.info(
                            f"Image generated for chapter {current_chapter_number}, sending update"
                        )
                        # Send image update for the chapter
                        await websocket.send_json(
                            {
                                "type": "chapter_image_update",
                                "chapter_number": current_chapter_number,
                                "image_data": image_data,
                            }
                        )
                else:
                    logger.warning(f"No image data generated for {identifier}")
            except Exception as e:
                logger.error(
                    f"Error waiting for image generation task {identifier}: {str(e)}"
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

    # Then send the completion message with stats and a button to view the summary
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
                "show_summary_button": True,  # Signal to show the summary button
                # Include chapter_summaries in the response for simulation logging
                "chapter_summaries": state.chapter_summaries,
            },
        }
    )


from app.services.llm.prompt_engineering import build_summary_chapter_prompt


async def generate_summary_content(state: AdventureState) -> str:
    """Generate summary content for the SUMMARY chapter.

    This function uses the stored chapter summaries to create a chronological
    recap of the adventure, along with a learning report showing all questions
    and answers.

    Args:
        state: The current adventure state

    Returns:
        The generated summary content
    """
    try:
        # Check if we have chapter summaries
        if state.chapter_summaries and len(state.chapter_summaries) > 0:
            logger.info(
                f"Using {len(state.chapter_summaries)} stored chapter summaries for summary content"
            )

            # Create the summary content with chapter summaries
            summary_content = "# Adventure Summary\n\n"

            # Add journey recap section with chapter summaries
            summary_content += "## Your Journey Recap\n\n"

            for i, summary in enumerate(state.chapter_summaries, 1):
                # Get the chapter type for context
                chapter_type = "Unknown"
                if i <= len(state.chapters):
                    chapter_type = state.chapters[i - 1].chapter_type.value.capitalize()

                # Get title from summary_chapter_titles if available
                title = f"Chapter {i}"
                if hasattr(state, "summary_chapter_titles") and i <= len(
                    state.summary_chapter_titles
                ):
                    title = state.summary_chapter_titles[i - 1]

                summary_content += f"### {title} ({chapter_type})\n"
                summary_content += f"{summary}\n\n"

            # Add learning report section
            summary_content += "\n\n# Learning Report\n\n"

            # Get all lesson chapters
            lesson_chapters = [
                chapter
                for chapter in state.chapters
                if chapter.chapter_type == ChapterType.LESSON and chapter.response
            ]

            if lesson_chapters:
                for i, chapter in enumerate(lesson_chapters, 1):
                    lesson_response = chapter.response
                    question = lesson_response.question["question"]
                    chosen_answer = lesson_response.chosen_answer
                    is_correct = lesson_response.is_correct

                    # Find the correct answer
                    correct_answer = next(
                        answer["text"]
                        for answer in lesson_response.question["answers"]
                        if answer["is_correct"]
                    )

                    # Get explanation if available
                    explanation = lesson_response.question.get("explanation", "")

                    summary_content += f"### Question {i}: {question}\n"
                    summary_content += f"- Your answer: {chosen_answer} "
                    summary_content += (
                        f"({'✓ Correct' if is_correct else '✗ Incorrect'})\n"
                    )

                    if not is_correct:
                        summary_content += f"- Correct answer: {correct_answer}\n"

                    if explanation:
                        summary_content += f"- Explanation: {explanation}\n"

                    summary_content += "\n"
            else:
                summary_content += "You didn't encounter any educational questions in this adventure.\n\n"

            # Add conclusion
            summary_content += "Thank you for joining us on this learning odyssey!\n"

            logger.info(
                "Generated summary content from stored summaries",
                extra={"content_length": len(summary_content)},
            )
            return summary_content
        else:
            logger.warning(
                "No chapter summaries available, falling back to LLM-generated summary"
            )
            # Fall back to the original method if no summaries are available
            system_prompt, user_prompt = build_summary_chapter_prompt(state)

            # Generate the summary content
            summary_content = ""
            async for chunk in llm_service.generate_with_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            ):
                summary_content += chunk

            logger.info(
                "Generated fallback summary content",
                extra={"content_length": len(summary_content)},
            )
            return summary_content

    except Exception as e:
        logger.error(f"Error generating summary content: {str(e)}")
        # Return a fallback summary if generation fails
        return """# Adventure Summary

## Your Journey Recap
You've completed an amazing educational adventure! Throughout your journey, you explored new worlds, 
made important choices, and learned valuable lessons.

## Learning Report
You answered several educational questions during your adventure. Some were challenging, 
but each one helped you grow and learn.

Thank you for joining us on this learning odyssey!
"""


# The process_summary_request function has been removed
# Its functionality is now handled by process_choice with the "reveal_summary" choice ID


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
    # Load story configuration using StoryLoader
    try:
        loader = StoryLoader()
        story_data = loader.load_all_stories()
        story_config = story_data["story_categories"][story_category]
    except Exception as e:
        logger.error(f"Error loading story data: {str(e)}")
        raise ValueError(f"Failed to load story data: {str(e)}")

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

            # Get difficulty from state metadata if available (for future difficulty toggle)
            difficulty = state.metadata.get("difficulty", "Reasonably Challenging")

            # Sample question with optional difficulty parameter
            question = sample_question(
                lesson_topic, exclude_questions=used_questions, difficulty=difficulty
            )

            logger.debug(f"DEBUG: Selected question: {question['question']}")
            logger.debug(f"DEBUG: Answers: {question['answers']}")
            logger.debug(
                f"DEBUG: Difficulty: {question.get('difficulty', 'Not specified')}"
            )
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

        # Validate and clean the content using Pydantic
        try:
            validated_content = ChapterContentValidator(content=story_content).content
            if validated_content != story_content:
                logger.info("Content was cleaned by ChapterContentValidator")
                logger.debug(f"Original content started with: {story_content[:50]}...")
                logger.debug(
                    f"Cleaned content starts with: {validated_content[:50]}..."
                )
            story_content = validated_content
        except Exception as e:
            logger.error(f"Error in Pydantic validation: {e}")
            # Fallback to regex if Pydantic validation fails
            story_content = re.sub(
                r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
                "",
                story_content,
                flags=re.IGNORECASE,
            )
            logger.debug("Fallback to regex cleaning after Pydantic validation failure")

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
            # Use the Pydantic validator to clean the content
            try:
                story_content = ChapterContentValidator(content=story_content).content
                if story_content != story_content:
                    logger.info(
                        "Content was cleaned by ChapterContentValidator in choice extraction"
                    )
            except Exception as e:
                logger.error(f"Error in Pydantic validation in choice extraction: {e}")
                # Fallback to regex if Pydantic validation fails
                story_content = re.sub(
                    r"^(?:#{1,6}\s+)?chapter(?:\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))?:?\s*",
                    "",
                    story_content,
                    flags=re.IGNORECASE,
                )
                logger.debug("Fallback to regex cleaning in choice extraction")

            story_content = story_content.strip()

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
    return ChapterContent(content=story_content, choices=story_choices), question
