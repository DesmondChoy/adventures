from typing import Dict, Any, Optional, Tuple, List
from fastapi import WebSocket
import logging
import re
import json
import asyncio

from app.models.story import (
    ChapterType,
    ChapterContent,
    StoryResponse,
    LessonResponse,
    ChapterData,
    AdventureState,
)
from app.services.adventure_state_manager import AdventureStateManager
from app.services.chapter_manager import ChapterManager
from app.services.state_storage_service import StateStorageService
from app.services.llm import LLMService
from app.services.llm.prompt_templates import CHARACTER_VISUAL_UPDATE_PROMPT

from .content_generator import generate_chapter
from .summary_generator import generate_summary_content, stream_summary_content

logger = logging.getLogger("story_app")
chapter_manager = ChapterManager()
state_storage_service = StateStorageService()
llm_service = LLMService()


async def handle_reveal_summary(
    state: AdventureState, state_manager: AdventureStateManager, websocket: WebSocket
) -> Tuple[None, None, bool]:
    """Handle the reveal_summary special choice."""
    logger.info("Processing reveal_summary choice")
    logger.info(f"Current state has {len(state.chapters)} chapters")
    logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")

    # Get the CONCLUSION chapter
    if state.chapters and state.chapters[-1].chapter_type == ChapterType.CONCLUSION:
        conclusion_chapter = state.chapters[-1]
        logger.info(f"Found CONCLUSION chapter: {conclusion_chapter.chapter_number}")
        logger.info(
            f"CONCLUSION chapter content length: {len(conclusion_chapter.content)}"
        )

        # Process it like a regular choice with placeholder values
        story_response = StoryResponse(chosen_path="reveal_summary", choice_text=" ")
        conclusion_chapter.response = story_response
        logger.info(
            "Created placeholder response for CONCLUSION chapter with whitespace"
        )

        await generate_conclusion_chapter_summary(conclusion_chapter, state, websocket)

    # Create and generate the SUMMARY chapter
    summary_chapter = chapter_manager.create_summary_chapter(state)
    summary_content = await generate_summary_content(state)
    summary_chapter.content = summary_content
    summary_chapter.chapter_content.content = summary_content

    # Add the SUMMARY chapter to the state
    state_manager.append_new_chapter(summary_chapter)

    await stream_summary_content(summary_content, websocket)

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


async def generate_conclusion_chapter_summary(
    conclusion_chapter: ChapterData, state: AdventureState, websocket: WebSocket
) -> None:
    """Generate and store summary for the conclusion chapter."""
    try:
        logger.info(f"Generating summary for CONCLUSION chapter")
        summary_result = await chapter_manager.generate_chapter_summary(
            conclusion_chapter.content,
            " ",  # Whitespace for chosen_choice
            " ",  # Whitespace for choice_context
        )

        # Extract title and summary from the result
        title = summary_result.get("title", "Chapter Summary")
        summary_text = summary_result.get("summary", "Summary not available")

        logger.info(f"Generated CONCLUSION chapter summary: {summary_text[:100]}...")

        # Store the summary
        if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
            logger.info(
                f"Adding placeholder summaries up to chapter {conclusion_chapter.chapter_number - 1}"
            )
            while len(state.chapter_summaries) < conclusion_chapter.chapter_number - 1:
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
                state.summary_chapter_titles[conclusion_chapter.chapter_number - 1] = (
                    title
                )

        logger.info(
            f"Stored summary for chapter {conclusion_chapter.chapter_number}: {summary_text}"
        )
        if hasattr(state, "summary_chapter_titles"):
            logger.info(
                f"Stored title for chapter {conclusion_chapter.chapter_number}: {title}"
            )

        # Store the updated state in StateStorageService
        state_id = await state_storage_service.store_state(state.dict())
        logger.info(
            f"Stored state with ID: {state_id} after generating CONCLUSION chapter summary"
        )

        # Include the state_id in the response to the client
        await websocket.send_json({"type": "summary_ready", "state_id": state_id})
    except Exception as e:
        logger.error(f"Error generating chapter summary: {str(e)}", exc_info=True)
        if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
            logger.warning(
                f"Using fallback summary for chapter {conclusion_chapter.chapter_number}"
            )
            state.chapter_summaries.append("Chapter summary not available")


async def diagnose_character_visuals(chapter_content, existing_visuals=None):
    """Diagnostic function to test character visual extraction from chapter content.

    Args:
        chapter_content: Content of the chapter to analyze
        existing_visuals: Dictionary of existing character visuals, if any

    Returns:
        Updated character visuals dictionary or None if extraction failed
    """
    if existing_visuals is None:
        existing_visuals = {}

    logger.info("Running character visual diagnostic")
    logger.info(f"Chapter content length: {len(chapter_content)}")
    logger.info(f"Existing visuals: {existing_visuals}")

    # Format the prompt with chapter content and existing visuals
    custom_prompt = CHARACTER_VISUAL_UPDATE_PROMPT.format(
        chapter_content=chapter_content,
        existing_visuals=json.dumps(existing_visuals, indent=2),
    )

    # Log a content snippet for debugging
    content_snippet = (
        chapter_content[:300] + "..." if len(chapter_content) > 300 else chapter_content
    )
    logger.debug(f"Chapter content snippet being analyzed: {content_snippet}")

    # Create a minimal state for the LLM call
    class MinimalState:
        def __init__(self):
            self.current_chapter_id = "character_visual_diagnostic"
            self.story_length = 1
            self.chapters = []
            self.metadata = {"prompt_override": True}

    minimal_state = MinimalState()

    # Use the LLM service to generate the result
    try:
        logger.info("Calling LLM for character visual diagnostic")
        chunks = []
        async for chunk in llm_service.generate_chapter_stream(
            story_config={},
            state=minimal_state,
            question=None,
            previous_lessons=None,
            context={"prompt_override": custom_prompt},
        ):
            chunks.append(chunk)

        response = "".join(chunks).strip()
        logger.debug(
            f"Raw LLM response: {response[:500]}..."
            if len(response) > 500
            else response
        )

        # Extract JSON object from the response using our enhanced parsing
        json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            logger.debug(f"Extracted JSON from markdown block")
        else:
            # If not found, look for any JSON-like structure with curly braces
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.debug(f"Extracted JSON-like structure")
            else:
                json_str = response
                logger.debug("Using entire response as JSON")

        # Try multiple parsing approaches
        try:
            updated_visuals = json.loads(json_str)
        except json.JSONDecodeError:
            # If parsing fails, try to clean the string and retry
            cleaned_json_str = json_str.replace("'", '"').replace("\\", "\\\\")
            try:
                updated_visuals = json.loads(cleaned_json_str)
            except json.JSONDecodeError:
                # Try regex extraction as last resort
                matches = re.findall(r'["\'](.*?)["\']: ["\'](.*?)["\']', response)
                if matches:
                    updated_visuals = {name: desc for name, desc in matches}
                    logger.info(
                        f"Extracted {len(updated_visuals)} character descriptions using regex"
                    )
                else:
                    logger.error("All JSON parsing approaches failed")
                    return None

        if not isinstance(updated_visuals, dict):
            logger.error(
                f"Invalid character visuals format - expected dict, got {type(updated_visuals)}"
            )
            return None

        logger.info("Successfully parsed character visuals:")
        for char_name, description in updated_visuals.items():
            logger.info(f'Character: "{char_name}", Description: "{description}"')

        return updated_visuals

    except Exception as e:
        logger.error(f"Error during character visual diagnostic: {e}")
        return None


async def fix_missing_character_visuals(
    state: AdventureState, state_manager: AdventureStateManager
) -> None:
    """Attempt to fix missing character visuals by analyzing all existing chapters.

    This function is useful when character visuals aren't being picked up properly and need to be
    retroactively extracted from existing chapter content.

    Args:
        state: Current adventure state
        state_manager: The AdventureStateManager instance
    """
    if not state or not state.chapters:
        logger.warning("No state or chapters to fix character visuals")
        return

    logger.info(
        f"Attempting to fix missing character visuals across {len(state.chapters)} chapters"
    )

    # Get existing character visuals or initialize empty dict
    existing_visuals = getattr(state, "character_visuals", {})
    logger.info(f"Starting with {len(existing_visuals)} existing character visuals")

    # Process each chapter in order
    for chapter in state.chapters:
        logger.info(
            f"Processing Chapter {chapter.chapter_number} for character visuals"
        )

        # Extract visuals from this chapter's content
        chapter_visuals = await diagnose_character_visuals(
            chapter.content, existing_visuals
        )

        if chapter_visuals:
            # Update our running dictionary with new/updated visuals
            existing_visuals.update(chapter_visuals)
            logger.info(f"Updated visuals, now have {len(existing_visuals)} characters")

    # Finally, update the state with all collected visuals
    if existing_visuals:
        logger.info(
            f"Updating state with {len(existing_visuals)} total character visuals"
        )
        state_manager.update_character_visuals(state, existing_visuals)
        logger.info("Character visuals fix complete")
    else:
        logger.warning("No character visuals found in any chapters")


async def _update_character_visuals(
    state: AdventureState, chapter_content: str, state_manager: AdventureStateManager
) -> None:
    """Update character visuals based on chapter content.

    This function extracts character descriptions from the chapter content
    and updates the character_visuals dictionary in the AdventureState.
    It uses an LLM to identify character descriptions and ensures they are
    properly persisted for image generation.

    Args:
        state: Current adventure state
        chapter_content: Content of the completed chapter
        state_manager: The AdventureStateManager instance
    """
    try:
        # Get chapter number for logging
        chapter_number = len(state.chapters)

        logger.info(
            f"[CHAPTER {chapter_number}] Starting character visual update from chapter content"
        )

        # Get existing character visuals or empty dict
        existing_visuals = getattr(state, "character_visuals", {})

        # Log the existing visuals
        logger.info(
            f"[CHAPTER {chapter_number}] AdventureState.character_visuals BEFORE update:"
        )
        if existing_visuals:
            for char_name, description in existing_visuals.items():
                logger.info(
                    f'[CHAPTER {chapter_number}] - {char_name}: "{description}"'
                )
        else:
            logger.info(
                f"[CHAPTER {chapter_number}] - Empty (no character visuals tracked yet)"
            )

        # Log base protagonist description
        protagonist_desc = getattr(state, "protagonist_description", "")
        if protagonist_desc:
            logger.info(
                f'[CHAPTER {chapter_number}] Base protagonist description: "{protagonist_desc}"'
            )

        # Log a content snippet for debugging - just for display purposes
        # Note: This is only truncated in the log, the full content is sent to the LLM
        content_snippet = (
            chapter_content[:300] + "..."
            if len(chapter_content) > 300
            else chapter_content
        )
        logger.debug(f"Chapter content snippet being analyzed (truncated for log display only): {content_snippet}")
        logger.debug(f"Full chapter content length: {len(chapter_content)} characters")

        # Format the prompt with chapter content and existing visuals
        custom_prompt = CHARACTER_VISUAL_UPDATE_PROMPT.format(
            chapter_content=chapter_content,
            existing_visuals=json.dumps(existing_visuals, indent=2),
        )

        # Log the prompt with distinctive markers for easier debugging in terminal logs
        logger.info(
            f"\n=== CHARACTER_VISUAL_UPDATE_PROMPT TRIGGERED [CHAPTER {chapter_number}] ===\n"
        )
        # Split the prompt into chunks for better readability in logs
        prompt_parts = custom_prompt.split("\n")
        beginning = "\n".join(prompt_parts[:15])  # First 15 lines
        middle_start = 15
        middle_end = (
            len(prompt_parts) - 15 if len(prompt_parts) > 30 else len(prompt_parts)
        )
        middle = "\n".join(prompt_parts[middle_start:middle_end])
        end = "\n".join(prompt_parts[-15:]) if len(prompt_parts) > 30 else ""

        logger.info(f"=== PROMPT BEGINNING ===\n{beginning}")
        if middle:
            logger.info(f"=== PROMPT MIDDLE ===\n{middle}")
        if end:
            logger.info(f"=== PROMPT END ===\n{end}")
        logger.info(f"=== END CHARACTER_VISUAL_UPDATE_PROMPT ===\n")

        # Also keep detailed debug log for full prompt
        logger.debug(f"Complete Character visual update prompt:\n{custom_prompt}")

        # Create a minimal state object for the LLM call
        class MinimalState:
            def __init__(self):
                self.current_chapter_id = "character_visual_update"
                self.story_length = 1
                self.chapters = []
                self.metadata = {"prompt_override": True}

        minimal_state = MinimalState()

        # Use the LLM service to generate the updated visuals
        try:
            logger.info(
                f"[CHAPTER {chapter_number}] Calling LLM for character visual updates"
            )
            # Extract a snippet for debugging purposes
            content_snippet = (
                chapter_content[:300] + "..."
                if len(chapter_content) > 300
                else chapter_content
            )
            logger.debug(f"Content being analyzed: {content_snippet}")

            chunks = []
            async for chunk in llm_service.generate_chapter_stream(
                story_config={},
                state=minimal_state,
                question=None,
                previous_lessons=None,
                context={"prompt_override": custom_prompt},
            ):
                chunks.append(chunk)

            response = "".join(chunks).strip()
            # Log the raw LLM response with distinctive markers
            logger.info(
                f"\n=== CHARACTER_VISUAL_UPDATE_PROMPT RESPONSE [CHAPTER {chapter_number}] ==="
            )
            # Avoid logging excessively long responses in INFO, but provide a meaningful excerpt
            if len(response) > 1000:
                logger.info(f"Response excerpt (first 500 chars):\n{response[:500]}")
                logger.info(f"Response excerpt (last 500 chars):\n{response[-500:]}")
                logger.info(
                    f"Full response logged at DEBUG level (length: {len(response)} chars)"
                )
            else:
                logger.info(f"Response:\n{response}")
            logger.info(f"=== END RESPONSE ===\n")

            # Keep detailed debug log
            logger.debug(f"Raw LLM response: {response}")

            # Enhanced JSON extraction and parsing
            logger.debug(f"Raw LLM response length: {len(response)}")
            logger.debug(f"First 200 chars: {response[:200]}")
            logger.debug(
                f"Last 200 chars: {response[-200:] if len(response) > 200 else response}"
            )

            # First, try to extract JSON between ```json and ``` markers
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug(f"Extracted JSON from markdown block: {json_str}")
            else:
                # If not found, look for any JSON-like structure with curly braces
                # The regex needs to be non-greedy to handle nested curly braces properly
                json_match = re.search(r"\{.*?\}", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.debug(f"Extracted JSON-like structure: {json_str}")
                else:
                    # Try a more comprehensive regex that can capture full JSON objects with nested structures
                    json_match = re.search(r"\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}", response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        logger.debug(f"Extracted complex JSON structure: {json_str}")
                    else:
                        # If still not found, try to use the entire response as JSON
                        json_str = response
                        logger.debug("Using entire response as JSON")

            # Parse the JSON with multiple fallback approaches
            try:
                updated_visuals = json.loads(json_str)
            except json.JSONDecodeError:
                # If parsing fails, try to clean the string and retry
                cleaned_json_str = json_str.replace("'", '"').replace("\\", "\\\\")
                logger.debug(
                    f"First JSON parse failed, trying with cleaned string: {cleaned_json_str[:100]}..."
                )
                try:
                    updated_visuals = json.loads(cleaned_json_str)
                except json.JSONDecodeError:
                    # Last resort: try multiple regex patterns to extract key-value pairs
                    logger.debug("Attempting regex extraction of key-value pairs")
                    
                    # Try standard JSON pattern first
                    matches = re.findall(
                        r'["\']([^"\']+)["\']:\s*["\']([^"\']+)["\']', response
                    )
                    
                    # If that doesn't work, try with double quotes only
                    if not matches:
                        logger.debug("First regex failed, trying double quotes only pattern")
                        matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', response)
                    
                    # If still no matches, try a more lenient pattern that doesn't require quotes for values
                    if not matches:
                        logger.debug("Second regex failed, trying lenient pattern")
                        matches = re.findall(r'"([^"]+)":\s*([^,}]+)', response)
                        # Clean up the matches to remove trailing whitespace and quotes
                        matches = [(k, v.strip().strip('"\'')) for k, v in matches]
                    
                    # If we found matches with any pattern, create the dictionary
                    if matches:
                        updated_visuals = {name: desc for name, desc in matches}
                        logger.info(
                            f"Extracted {len(updated_visuals)} character descriptions using regex pattern"
                        )
                    else:
                        # Last attempt: look for "You" or protagonist as a character if nothing else worked
                        protagonist_desc = getattr(state, "protagonist_description", "")
                        if protagonist_desc:
                            logger.info("Creating fallback visuals with protagonist only")
                            updated_visuals = {"You": protagonist_desc}
                        else:
                            logger.error("All JSON parsing approaches failed")
                            return

            if not isinstance(updated_visuals, dict):
                logger.error(
                    f"Invalid character visuals format - expected dict, got {type(updated_visuals)}"
                )
                return

            # Log parsing success with distinctive markers
            logger.info(
                f"\n=== CHARACTER VISUALS PARSED [CHAPTER {chapter_number}] ==="
            )
            logger.info(
                f"Successfully extracted {len(updated_visuals)} character descriptions"
            )

            # Log the extracted character visuals
            for char_name, description in updated_visuals.items():
                logger.info(f'- {char_name}: "{description}"')
            logger.info(f"=== END CHARACTER VISUALS ===\n")

            # Keep detailed debug log
            logger.debug(
                f"Successfully parsed character visuals with {len(updated_visuals)} entries"
            )

            # Update the state with the new visuals
            state_manager.update_character_visuals(state, updated_visuals)
            logger.info(
                f"[CHAPTER {chapter_number}] Successfully updated character visuals with {len(updated_visuals)} entries"
            )

        except json.JSONDecodeError as e:
            logger.error(
                f"[CHAPTER {chapter_number}] Failed to parse JSON from LLM response: {e}"
            )
            logger.debug(f"Raw response causing JSONDecodeError: {response}")
        except Exception as e:
            logger.error(
                f"[CHAPTER {chapter_number}] Error generating character visuals: {e}"
            )

    except Exception as e:
        logger.error(f"Error in _update_character_visuals: {e}")
        # Don't re-raise - this is an auxiliary function that shouldn't block the main flow


async def process_non_start_choice(
    chosen_path: str,
    choice_text: str,
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process a non-start choice from the user."""
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
        await process_lesson_response(previous_chapter, choice_text, state, websocket)
    else:
        await process_story_response(previous_chapter, chosen_path, choice_text, state)

    # Generate a chapter summary for the previous chapter
    await generate_chapter_summary(previous_chapter, state)

    # Update character visuals asynchronously based on the completed chapter
    # This runs in the background and doesn't block the main flow
    character_visual_task = asyncio.create_task(
        _update_character_visuals(state, previous_chapter.content, state_manager)
    )

    # Add task completion callback to track success/failure
    character_visual_task.add_done_callback(
        lambda t: logger.info(
            f"Character visual update task completed: {t.exception() or 'Successfully'}"
        )
    )

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
    new_chapter = await create_and_append_chapter(
        chapter_content, chapter_type, sampled_question, state_manager, websocket
    )
    if not new_chapter:
        return None, None, False

    # Check if story is complete - when we've reached the story length
    is_story_complete = len(state.chapters) == state.story_length

    return chapter_content, sampled_question, is_story_complete


async def process_start_choice(
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool]:
    """Process the start choice (first chapter)."""
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
    new_chapter = await create_and_append_chapter(
        chapter_content, chapter_type, sampled_question, state_manager, None
    )

    if new_chapter:
        # Extract character visuals from the first chapter content
        # This needs to happen immediately for Chapter 1 since we need visuals for image generation
        logger.info("\nExtracting character visuals from Chapter 1 content")
        await _update_character_visuals(state, new_chapter.content, state_manager)

    # No need to process previous chapter for start choice
    is_story_complete = False

    return chapter_content, sampled_question, is_story_complete


async def process_lesson_response(
    previous_chapter: ChapterData,
    choice_text: str,
    state: AdventureState,
    websocket: WebSocket,
) -> None:
    """Process a response to a lesson chapter."""
    logger.debug("\n=== DEBUG: Processing Lesson Response ===")
    logger.debug(f"Previous chapter number: {previous_chapter.chapter_number}")
    logger.debug(
        f"Previous chapter has question: {previous_chapter.question is not None}"
    )

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
                "question": previous_chapter.question.get(
                    "question", "Unknown question"
                ),
                "answers": previous_chapter.question.get("answers", []),
                "chosen_answer": choice_text,
                "is_correct": choice_text == correct_answer,
                "explanation": previous_chapter.question.get("explanation", ""),
                "correct_answer": correct_answer,
            }

            # Append to state's lesson_questions
            state.lesson_questions.append(question_obj)
            logger.info(
                f"Added question to lesson_questions array: {question_obj['question']}"
            )

            logger.debug("\n=== DEBUG: Created Lesson Response ===")
            logger.debug(f"Question: {previous_chapter.question['question']}")
            logger.debug(f"Chosen answer: {choice_text}")
            logger.debug(f"Correct answer: {correct_answer}")
            logger.debug(f"Is correct: {choice_text == correct_answer}")
            logger.debug(
                f"Questions in lesson_questions: {len(state.lesson_questions)}"
            )
            logger.debug("====================================\n")
        else:
            logger.error("Previous chapter missing question data")
            await websocket.send_text(
                "An error occurred while processing your answer. Missing question data."
            )
            raise ValueError("Missing question data in chapter")
    except Exception as e:
        logger.error(f"Error creating lesson response: {e}")
        await websocket.send_text(
            "An error occurred while processing your answer. Please try again."
        )
        raise ValueError(f"Error processing lesson response: {str(e)}")


async def process_story_response(
    previous_chapter: ChapterData,
    chosen_path: str,
    choice_text: str,
    state: AdventureState,
) -> None:
    """Process a response to a story chapter."""
    story_response = StoryResponse(chosen_path=chosen_path, choice_text=choice_text)
    previous_chapter.response = story_response
    logger.debug(f"Created story response: {story_response}")

    # Handle first chapter agency choice
    if (
        previous_chapter.chapter_number == 1
        and previous_chapter.chapter_type == ChapterType.STORY
    ):
        logger.debug("Processing first chapter agency choice")

        # Extract agency category and visual details
        agency_category = ""
        visual_details = ""

        # Try to find the matching agency option
        try:
            from app.services.llm.prompt_templates import categories

            for category_name, category_options in categories.items():
                for option in category_options:
                    # Extract the name part (before the bracket)
                    option_name = option.split("[")[0].strip()
                    # Check if this option matches the choice text
                    if (
                        option_name.lower() in choice_text.lower()
                        or choice_text.lower() in option_name.lower()
                    ):
                        agency_category = category_name
                        # Extract visual details from square brackets
                        match = re.search(r"\[(.*?)\]", option)
                        if match:
                            visual_details = match.group(1)
                        break
                if visual_details:
                    break
        except Exception as e:
            logger.error(f"Error extracting agency details: {e}")

        # Store agency choice in metadata with visual details
        state.metadata["agency"] = {
            "type": "choice",
            "name": "from Chapter 1",
            "description": choice_text,
            "category": agency_category,
            "visual_details": visual_details,
            "properties": {"strength": 1},
            "growth_history": [],
            "references": [],
        }

        # Add agency to character_visuals dictionary for image generation
        # Since this is agency-specific info that might not be captured by normal character extraction
        if visual_details and "character_visuals" in state.__dict__:
            agency_name = (
                choice_text.split("-")[0].strip() if "-" in choice_text else choice_text
            )

            # If specific object/companion names are in the agency choice, extract those
            refined_name = (
                agency_name.split(":")[-1].strip()
                if ":" in agency_name
                else agency_name
            )

            # Add to character_visuals with special prefix to identify as agency
            state.character_visuals["AGENCY_" + refined_name] = visual_details
            logger.info(
                f"Added agency to character_visuals: {refined_name} - {visual_details}"
            )

        logger.debug(f"Stored agency choice from Chapter 1: {choice_text}")
        logger.debug(f"Agency category: {agency_category}")
        logger.debug(f"Visual details: {visual_details}")


async def generate_chapter_summary(
    previous_chapter: ChapterData, state: AdventureState
) -> None:
    """Generate a summary for the previous chapter."""
    try:
        logger.info(f"Generating summary for chapter {previous_chapter.chapter_number}")

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

        await store_chapter_summary(previous_chapter, state, title, summary_text)
    except Exception as e:
        logger.error(f"Error generating chapter summary: {str(e)}")
        # Don't fail the whole process if summary generation fails
        if len(state.chapter_summaries) < previous_chapter.chapter_number:
            state.chapter_summaries.append("Chapter summary not available")


async def store_chapter_summary(
    chapter: ChapterData, state: AdventureState, title: str, summary_text: str
) -> None:
    """Store chapter summary and title in the state."""
    if len(state.chapter_summaries) < chapter.chapter_number:
        # If this is the first summary, we might need to add placeholders for previous chapters
        while len(state.chapter_summaries) < chapter.chapter_number - 1:
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
        state.chapter_summaries[chapter.chapter_number - 1] = summary_text
        # Replace the title if the field exists
        if hasattr(state, "summary_chapter_titles"):
            # Ensure the list is long enough
            while len(state.summary_chapter_titles) < chapter.chapter_number:
                state.summary_chapter_titles.append(
                    f"Chapter {len(state.summary_chapter_titles) + 1}"
                )
            state.summary_chapter_titles[chapter.chapter_number - 1] = title

    logger.info(f"Stored summary for chapter {chapter.chapter_number}: {summary_text}")
    if hasattr(state, "summary_chapter_titles"):
        logger.info(f"Stored title for chapter {chapter.chapter_number}: {title}")


async def create_and_append_chapter(
    chapter_content: ChapterContent,
    chapter_type: ChapterType,
    sampled_question: Optional[Dict[str, Any]],
    state_manager: AdventureStateManager,
    websocket: Optional[WebSocket],
) -> Optional[ChapterData]:
    """Create and append a new chapter to the state."""
    from .content_generator import clean_chapter_content

    try:
        # Use the Pydantic validator to clean the content
        validated_content = clean_chapter_content(chapter_content.content)

        new_chapter = ChapterData(
            chapter_number=len(state_manager.get_current_state().chapters) + 1,
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
        return new_chapter
    except ValueError as e:
        logger.error(f"Error adding chapter: {e}")
        if websocket:  # Only send message if websocket is provided
            await websocket.send_text(
                "An error occurred while processing your choice. Please try again."
            )
        return None
