from typing import Dict, Any, Optional, Tuple, List
from fastapi import WebSocket
import logging
import re
import json
import asyncio
import time  # Added import
from uuid import UUID

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
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.prompt_templates import CHARACTER_VISUAL_UPDATE_PROMPT
from app.services.telemetry_service import TelemetryService

from .content_generator import generate_chapter
from .summary_generator import generate_summary_content, stream_summary_content

logger = logging.getLogger("story_app")
chapter_manager = ChapterManager()
state_storage_service = StateStorageService()
# Lazy instantiation to avoid module-level factory creation
_llm_service = None

def get_llm_service():
    """Get LLM service instance with lazy instantiation."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMServiceFactory.create_for_use_case("character_visual_processing")
    return _llm_service

# Lazy instantiation to avoid environment variable loading issues during import
_telemetry_service = None


def get_telemetry_service():
    """Get or create the telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service


async def handle_reveal_summary(
    state: AdventureState,
    state_manager: AdventureStateManager,
    websocket: WebSocket,
    connection_data: Optional[Dict[str, Any]] = None,
) -> Tuple[None, None, bool]:
    """Handle the reveal_summary special choice."""
    logger.info("[REVEAL SUMMARY] Processing reveal_summary choice")
    logger.info(f"[REVEAL SUMMARY] State has {len(state.chapters)} chapters before processing")
    logger.info(f"[REVEAL SUMMARY] Current storytelling phase: {state.current_storytelling_phase}")
    for i, ch in enumerate(state.chapters):
        logger.info(f"[REVEAL SUMMARY] Chapter {i+1}: type={ch.chapter_type}, number={ch.chapter_number}")
    logger.info(f"Current state has {len(state.chapters)} chapters")
    logger.info(f"Current chapter summaries: {len(state.chapter_summaries)}")
    
    # Wait for any pending summary tasks to complete before revealing summary
    if state.pending_summary_tasks:
        logger.info(f"[REVEAL SUMMARY] Waiting for {len(state.pending_summary_tasks)} pending summary tasks to complete")
        await asyncio.gather(*state.pending_summary_tasks, return_exceptions=True)
        state.pending_summary_tasks.clear()
        logger.info("[REVEAL SUMMARY] All pending summary tasks completed")
    
    # Ensure all chapter summaries exist (on-demand generation for missing ones)
    from app.services.websocket.summary_generator import ensure_all_summaries_exist
    await ensure_all_summaries_exist(state)

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

        # Complete ALL state operations BEFORE sending navigation signal
        conclusion_state_id = await generate_conclusion_chapter_summary(
            conclusion_chapter, state, websocket, connection_data, send_ready_signal=False
        )

        # Create and generate the SUMMARY chapter
        summary_chapter = chapter_manager.create_summary_chapter(state)
        summary_content = await generate_summary_content(state)
        summary_chapter.content = summary_content
        summary_chapter.chapter_content.content = summary_content

        # Add the SUMMARY chapter to the state
        state_manager.append_new_chapter(summary_chapter)

        # Save final complete state with all chapters
        state_storage_service = StateStorageService()
        adventure_id = connection_data.get("adventure_id") if connection_data else None
        
        final_state_id = await state_storage_service.store_state(
            state.model_dump(mode='json'),
            adventure_id=adventure_id,
            user_id=connection_data.get("user_id") if connection_data else None,
            explicit_is_complete=True,
        )
        
        logger.info(f"Saved final complete state with {len(state.chapters)} chapters, ID: {final_state_id}")

        # NOW send navigation signal after all state is saved
        await websocket.send_json({"type": "summary_ready", "state_id": final_state_id})
        
        # Skip streaming to avoid WebSocket disconnection errors  
        logger.info("Summary ready signal sent, skipping streaming to prevent disconnection errors")

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

    return None, None, False, False


async def generate_conclusion_chapter_summary(
    conclusion_chapter: ChapterData,
    state: AdventureState,
    websocket: WebSocket,
    connection_data: Optional[Dict[str, Any]] = None,
    send_ready_signal: bool = True,
) -> str:
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
        adventure_id = None

        # Use existing adventure_id if available in connection_data
        if connection_data and "adventure_id" in connection_data:
            adventure_id = connection_data["adventure_id"]
            logger.info(
                f"Using existing adventure_id: {adventure_id} for state storage"
            )

            # Update the existing record with is_complete=True
            # Update the existing record with is_complete=True
            state_id = await state_storage_service.store_state(
                state.model_dump(mode='json'),
                adventure_id=adventure_id,
                user_id=None,  # No authenticated user yet
                explicit_is_complete=True,  # Mark as complete
            )
            logger.info(
                f"Updated state with ID: {state_id} (is_complete=True) after generating CONCLUSION chapter summary"
            )
        else:
            # Create a new record if no adventure_id is available
            state_id = await state_storage_service.store_state(
                state.model_dump(mode='json'),
                explicit_is_complete=True,  # Mark as complete
            )
            logger.info(
                f"Stored new state with ID: {state_id} (is_complete=True) after generating CONCLUSION chapter summary"
            )

        # Conditionally send ready signal based on parameter
        if send_ready_signal:
            await websocket.send_json({"type": "summary_ready", "state_id": state_id})
        
        return state_id  # Return state_id for caller to use
    except Exception as e:
        logger.error(f"Error generating chapter summary: {str(e)}", exc_info=True)
        if len(state.chapter_summaries) < conclusion_chapter.chapter_number:
            logger.warning(
                f"Using fallback summary for chapter {conclusion_chapter.chapter_number}"
            )
            state.chapter_summaries.append("Chapter summary not available")
        return None  # Return None if error occurs


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
        async for chunk in get_llm_service().generate_chapter_stream(
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


# This function is no longer needed since we use the non-streaming API directly


async def extract_character_visuals_from_response(response, chapter_number):
    """Extract character visuals from LLM response with reliable JSON parsing.

    Args:
        response: Complete LLM response text from non-streaming API
        chapter_number: Current chapter number for logging

    Returns:
        dict: Extracted character visuals dictionary or empty dict if extraction failed
    """
    # Log what we're working with
    logger.info(
        f"[CHAPTER {chapter_number}] Extracting character visuals from response of length {len(response)}"
    )
    if response:
        logger.info(f"[CHAPTER {chapter_number}] Response excerpt: {response[:100]}...")
    else:
        logger.error(f"[CHAPTER {chapter_number}] Empty response received from LLM")
        return {}

    # First try to extract from markdown JSON code block (common LLM response format)
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        logger.info(f"[CHAPTER {chapter_number}] Found JSON in markdown code block")

        try:
            updated_visuals = json.loads(json_str)
            if isinstance(updated_visuals, dict):
                logger.info(
                    f"[CHAPTER {chapter_number}] Successfully parsed JSON from markdown block"
                )
                return updated_visuals
        except json.JSONDecodeError as e:
            logger.warning(
                f"[CHAPTER {chapter_number}] JSON from markdown block parse error: {e}"
            )

    # Try parsing the direct response if it looks like JSON
    try:
        if response.strip().startswith("{") and response.strip().endswith("}"):
            direct_json = json.loads(response)
            if isinstance(direct_json, dict):
                logger.info(
                    f"[CHAPTER {chapter_number}] Successfully parsed direct JSON response"
                )
                return direct_json
    except json.JSONDecodeError:
        logger.debug(
            f"[CHAPTER {chapter_number}] Response is not directly parseable as JSON"
        )

    # Fallback regex pattern for JSON-like structures
    pattern = r"\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}"
    json_matches = re.findall(pattern, response, re.DOTALL)

    if json_matches:
        # Try each match, starting with the longest
        for json_str in sorted(json_matches, key=len, reverse=True):
            try:
                updated_visuals = json.loads(json_str)
                if isinstance(updated_visuals, dict):
                    logger.info(
                        f"[CHAPTER {chapter_number}] Successfully parsed JSON from regex match"
                    )
                    return updated_visuals
            except json.JSONDecodeError:
                continue

    # Ultimate fallback - return empty dict
    logger.error(f"[CHAPTER {chapter_number}] All JSON extraction methods failed")
    return {}


def validate_character_visuals(visuals):
    """Validate that the extracted character visuals are in the expected format.

    Args:
        visuals: Dictionary of character visuals to validate

    Returns:
        bool: True if visuals are valid, False otherwise
    """
    if not isinstance(visuals, dict):
        return False

    # Check that we have at least one character
    if len(visuals) == 0:
        return False

    # Check that values are all strings
    for name, description in visuals.items():
        if not isinstance(name, str) or not isinstance(description, str):
            return False

    return True


async def _update_character_visuals(
    state: AdventureState, chapter_content: str, state_manager: AdventureStateManager
) -> dict:
    """Update character visuals based on chapter content.

    This function extracts character descriptions from the chapter content
    and updates the character_visuals dictionary in the AdventureState.
    It uses an LLM to identify character descriptions and ensures they are
    properly persisted for image generation.

    Args:
        state: Current adventure state
        chapter_content: Content of the completed chapter
        state_manager: The AdventureStateManager instance

    Returns:
        dict: The updated visuals dictionary for immediate use or None on failure
    """
    try:
        # Get chapter number for logging
        chapter_number = len(state.chapters)

        logger.info(
            f"[CHAPTER {chapter_number}] Starting character visual update from chapter content"
        )

        # Get existing character visuals or empty dict - we need this for the prompt
        # but we'll avoid logging it to keep the terminal cleaner and more focused
        existing_visuals = getattr(state, "character_visuals", {})

        # Just log how many existing visuals we have, not the details (we'll log final result at the end)
        logger.info(
            f"[CHAPTER {chapter_number}] Starting with {len(existing_visuals)} existing character visual entries"
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
        logger.debug(
            f"Chapter content snippet being analyzed (truncated for log display only): {content_snippet}"
        )
        logger.debug(
            f"Full chapter content length: {len(chapter_content)} characters\n"
        )

        # Format the prompt using string replacement for safer substitution
        try:
            existing_visuals_json = json.dumps(existing_visuals, indent=2)
            # Directly substitute using string replacement.
            custom_prompt = CHARACTER_VISUAL_UPDATE_PROMPT.replace(
                "{chapter_content}", chapter_content
            ).replace("{existing_visuals}", existing_visuals_json)
            # Log success for debugging
            logger.debug(
                "Successfully formatted CHARACTER_VISUAL_UPDATE_PROMPT using .replace()"
            )

        except Exception as e:
            # Log the specific error during formatting
            logger.error(
                f"Error formatting prompt using .replace(): {e}", exc_info=True
            )
            # Fallback to a simpler f-string based prompt if replacement fails
            logger.warning("Falling back to simplified prompt formatting due to error.")
            existing_visuals_json = json.dumps(existing_visuals, indent=2)
            custom_prompt = f"""
ROLE: Visual Character Tracker

TASK:
Extract character visual descriptions from this chapter and return JSON.

CHAPTER CONTENT:
{chapter_content}

EXISTING VISUALS:
{json.dumps(existing_visuals, indent=2)}

OUTPUT FORMAT:
Return ONLY a valid JSON with character names and descriptions.
            """

        # Log the prompt with distinctive markers for easier debugging in terminal logs
        logger.info(
            f"\n=== CHARACTER_VISUAL_UPDATE_PROMPT TRIGGERED [CHAPTER {chapter_number}] ===\n"
        )
        logger.info(
            f"Character visual update prompt for chapter {chapter_number} (content length: {len(chapter_content)} chars)"
        )
        logger.info(f"=== END CHARACTER_VISUAL_UPDATE_PROMPT ===\n")

        # Keep detailed debug log for full prompt if needed
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

            # IMPORTANT: Use the non-streaming API for character visuals
            # This directly gets the complete, synchronous response
            logger.info(
                f"[CHAPTER {chapter_number}] Using non-streaming API for character visuals"
            )
            response = await get_llm_service().generate_character_visuals_json(custom_prompt)

            # Log the raw LLM response with distinctive markers
            logger.info(
                f"\n=== LLM_RESPONSE: CHARACTER_VISUAL_UPDATE_PROMPT [CHAPTER {chapter_number}] ==="
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

            # Extract JSON directly from the complete response
            updated_visuals = await extract_character_visuals_from_response(
                response, chapter_number
            )

            if not validate_character_visuals(updated_visuals):
                logger.error(
                    f"[CHAPTER {chapter_number}] Character visuals validation failed"
                )
                # Try to use protagonist as fallback if nothing else worked
                protagonist_desc = getattr(state, "protagonist_description", "")
                if protagonist_desc:
                    logger.info(
                        f"[CHAPTER {chapter_number}] Creating fallback visuals with protagonist only"
                    )
                    updated_visuals = {"You": protagonist_desc}
                else:
                    logger.error(
                        f"[CHAPTER {chapter_number}] No visuals could be extracted and no protagonist fallback available"
                    )
                    return None

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

            # Ensure the character_visuals attribute exists before updating
            if not hasattr(state, "character_visuals"):
                logger.info(
                    f"[CHAPTER {chapter_number}] Initializing character_visuals attribute in state"
                )
                state.character_visuals = {}

            # Update the state with the new visuals
            state_manager.update_character_visuals(state, updated_visuals)

            # Show the character visuals after updating - this is what matters to users
            logger.info(
                f"\n=== CHARACTER VISUALS TRACKED [CHAPTER {chapter_number}] ==="
            )
            # Get the updated character visuals
            after_visuals = getattr(state, "character_visuals", {})
            if after_visuals:
                # Sort by key to make it easier to scan
                for char_name, description in sorted(after_visuals.items()):
                    logger.info(f'- {char_name}: "{description}"')
            else:
                logger.info("- Empty (no character visuals being tracked)")
            logger.info(f"=== END CHARACTER VISUALS ===\n")

            logger.info(
                f"[CHAPTER {chapter_number}] Successfully updated character visuals with {len(updated_visuals)} entries"
            )

            return updated_visuals

        except json.JSONDecodeError as e:
            logger.error(
                f"[CHAPTER {chapter_number}] Failed to parse JSON from LLM response: {e}"
            )
            logger.debug(f"Raw response causing JSONDecodeError: {response}")
            return None
        except Exception as e:
            logger.error(
                f"[CHAPTER {chapter_number}] Error generating character visuals: {e}"
            )
            return None

    except Exception as e:
        logger.error(f"Error in _update_character_visuals: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")

        # Add more debugging info
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # Try to create a fallback with protagonist only
        try:
            protagonist_desc = getattr(state, "protagonist_description", "")
            if protagonist_desc and state and hasattr(state, "character_visuals"):
                logger.info("Creating fallback protagonist entry after error")
                state.character_visuals["You"] = protagonist_desc
                return {"You": protagonist_desc}
            return None
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback: {fallback_error}")
            return None


async def process_non_start_choice(
    chosen_path: str,
    choice_text: str,
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
    websocket: WebSocket,
    connection_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool, bool]:
    """Process a non-start choice from the user."""
    logger.info(f"[ADVENTURE FLOW] Processing non-start choice: {chosen_path}")
    logger.info(f"[ADVENTURE FLOW] Current state chapters: {len(state.chapters)}")
    logger.info(f"[ADVENTURE FLOW] Current storytelling phase: {state.current_storytelling_phase}")
    
    # LOG EXISTING CHAPTER TYPES
    for i, ch in enumerate(state.chapters):
        logger.info(f"[ADVENTURE FLOW] Existing Chapter {i+1}: type={ch.chapter_type}, number={ch.chapter_number}")

    current_chapter_number = len(state.chapters) + 1
    logger.info(f"[ADVENTURE FLOW] Processing chapter {current_chapter_number}")
    
    # LOG PLANNED CHAPTER TYPES
    logger.info(f"[ADVENTURE FLOW] Planned chapter types: {state.planned_chapter_types}")
    
    chapter_type = state.planned_chapter_types[current_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)
    logger.info(f"[ADVENTURE FLOW] Next chapter type: {chapter_type}")
    
    # CHECK IF THIS IS THE FINAL CHAPTER
    is_final_chapter = current_chapter_number >= state.story_length
    logger.info(f"[ADVENTURE FLOW] Is final chapter (#{current_chapter_number} >= {state.story_length}): {is_final_chapter}")

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

    # Calculate event_duration_ms for 'choice_made'
    calculated_duration_ms: Optional[int] = None
    start_time_ms = None
    
    # Try to get start time from connection_data first (for active connections)
    if connection_data and isinstance(connection_data, dict):
        start_time_ms = connection_data.pop("current_chapter_start_time_ms", None)
    
    # If not in connection_data, try to get from adventure state metadata (for reconnected sessions)
    if start_time_ms is None:
        start_time_ms = state.metadata.get(f"chapter_{previous_chapter.chapter_number}_start_time_ms")
        
    if start_time_ms is not None:
        current_time_ms = int(time.time() * 1000)
        calculated_duration_ms = current_time_ms - start_time_ms
        logger.info(
            f"Calculated time spent on chapter {previous_chapter.chapter_number}: {calculated_duration_ms} ms"
        )
    else:
        logger.debug(
            f"Chapter start time not available for chapter {previous_chapter.chapter_number}. Duration will be null (likely due to connection restart)."
        )

    calculated_duration_seconds: Optional[int] = None
    if calculated_duration_ms is not None:
        calculated_duration_seconds = round(calculated_duration_ms / 1000)

    # Log choice_made event
    try:
        event_metadata = {
            "chapter_number": previous_chapter.chapter_number,
            "chapter_type": previous_chapter.chapter_type.value,
            "choice_text": choice_text,
            "story_category": story_category,
            "lesson_topic": lesson_topic,
            "client_uuid": connection_data.get("client_uuid")
            if connection_data
            else None,
        }
        if previous_chapter.chapter_type == ChapterType.STORY:
            event_metadata["chosen_path"] = chosen_path
        elif previous_chapter.chapter_type == ChapterType.LESSON and isinstance(
            previous_chapter.response, LessonResponse
        ):
            event_metadata["is_correct"] = previous_chapter.response.is_correct

        event_metadata = {k: v for k, v in event_metadata.items() if v is not None}

        current_adventure_id = (
            connection_data.get("adventure_id") if connection_data else None
        )
        await get_telemetry_service().log_event(
            event_name="choice_made",
            adventure_id=UUID(current_adventure_id) if current_adventure_id else None,
            user_id=connection_data.get("user_id") if connection_data else None,
            metadata=event_metadata,
            chapter_type=previous_chapter.chapter_type.value,
            chapter_number=previous_chapter.chapter_number,
            event_duration_seconds=calculated_duration_seconds,
        )
        logger.info(
            f"Logged 'choice_made' event for adventure ID: {current_adventure_id}, chapter: {previous_chapter.chapter_number}, duration: {calculated_duration_seconds} s"
        )
    except Exception as tel_e:
        logger.error(f"Error logging 'choice_made' event: {tel_e}")

    # Defer chapter summary generation until after streaming completes (Phase 1 streaming fix)
    logger.info(f"[PERFORMANCE] Deferring background chapter summary for chapter {previous_chapter.chapter_number} until after streaming")
    
    # Create a deferred task factory that will be executed after streaming
    def create_summary_task():
        task = asyncio.create_task(generate_chapter_summary_background(previous_chapter, state))
        state.pending_summary_tasks.append(task)
        
        # Add error visibility callback
        def _log_task_error(task: asyncio.Task) -> None:
            if task.exception():
                logger.error(f"Summary task crashed: {task.exception()}")
        
        task.add_done_callback(_log_task_error)
        logger.info(f"[PERFORMANCE] Chapter summary task started in background after streaming completed")
        return task
    
    # Store the deferred task to be executed after streaming
    state.deferred_summary_tasks.append(create_summary_task)
    logger.info(f"[PERFORMANCE] Chapter summary task deferred, continuing with next chapter generation")

    # Defer character visual extraction until after streaming completes (Phase 2 streaming fix)
    logger.info(f"[PERFORMANCE] Deferring character visual extraction for chapter {previous_chapter.chapter_number} until after streaming")
    
    # Create a deferred task factory for character visual extraction
    def create_visual_extraction_task():
        task = asyncio.create_task(_update_character_visuals_background(previous_chapter, state, state_manager))
        state.pending_summary_tasks.append(task)  # Reuse existing task tracking
        
        # Add error visibility callback
        def _log_visual_task_error(task: asyncio.Task) -> None:
            if task.exception():
                logger.error(f"Character visual extraction task crashed: {task.exception()}")
        
        task.add_done_callback(_log_visual_task_error)
        logger.info(f"[PERFORMANCE] Character visual extraction task started in background after streaming completed")
        return task
    
    # Store the deferred visual extraction task
    state.deferred_summary_tasks.append(create_visual_extraction_task)
    logger.info(f"[PERFORMANCE] Character visual extraction deferred, continuing with next chapter generation")
    
    # Skip synchronous visual extraction for now - it will happen after streaming
    # No need to process visual extraction results here since it's deferred

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

    # Use live streaming generation instead of blocking collection
    from .stream_handler import stream_chapter_with_live_generation, create_and_append_chapter_direct
    
    logger.info(f"[PERFORMANCE] Attempting live streaming for chapter {len(state.chapters) + 1}")
    try:
        content_to_stream, sampled_question, chapter_content = await stream_chapter_with_live_generation(
            story_category, lesson_topic, state, websocket, state_manager
        )
        logger.info(f"[PERFORMANCE] Live streaming successful for chapter {len(state.chapters) + 1}")
        
        # Create and append chapter without additional streaming (already done)
        new_chapter = await create_and_append_chapter_direct(
            chapter_content, chapter_type, sampled_question, state, state_manager
        )
        
        if not new_chapter:
            return None, None, False, False
            
        # Check if story is complete - when we've reached the story length
        is_story_complete = len(state.chapters) == state.story_length
        
        # Return with flag indicating content was already streamed live
        return chapter_content, sampled_question, is_story_complete, True
        
    except Exception as e:
        logger.error(f"[PERFORMANCE] Live streaming failed, falling back to traditional method: {e}")
        
        # Fallback to original blocking method
        chapter_content, sampled_question = await generate_chapter(
            story_category, lesson_topic, state
        )

        # Create and append new chapter
        new_chapter = await create_and_append_chapter(
            chapter_content, chapter_type, sampled_question, state_manager, websocket
        )
        if not new_chapter:
            return None, None, False, False

        # Check if story is complete - when we've reached the story length
        is_story_complete = len(state.chapters) == state.story_length

        return chapter_content, sampled_question, is_story_complete, False


async def process_start_choice(
    state: AdventureState,
    state_manager: AdventureStateManager,
    story_category: str,
    lesson_topic: str,
    websocket: Optional[WebSocket] = None,
    connection_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[ChapterContent], Optional[dict], bool, bool]:
    """Process the start choice (first chapter) with live streaming."""
    # Calculate new chapter number and update story phase
    new_chapter_number = len(state.chapters) + 1
    chapter_type = state.planned_chapter_types[new_chapter_number - 1]
    if not isinstance(chapter_type, ChapterType):
        chapter_type = ChapterType(chapter_type)

    # Update the storytelling phase based on the new chapter number
    state.current_storytelling_phase = ChapterManager.determine_story_phase(
        new_chapter_number, state.story_length
    )

    # Use live streaming generation instead of blocking collection
    from .stream_handler import stream_chapter_with_live_generation, create_and_append_chapter_direct
    
    logger.info(f"[PERFORMANCE] Attempting live streaming for Chapter 1")
    try:
        content_to_stream, sampled_question, chapter_content = await stream_chapter_with_live_generation(
            story_category, lesson_topic, state, websocket, state_manager
        )
        logger.info(f"[PERFORMANCE] Live streaming successful for Chapter 1")
        
        # Create and append chapter without additional streaming (already done)
        new_chapter = await create_and_append_chapter_direct(
            chapter_content, chapter_type, sampled_question, state, state_manager
        )
        
        if not new_chapter:
            return None, None, False, False
            
        # Defer character visual extraction to background (same as other chapters)
        if new_chapter:
            try:
                logger.info("[PERFORMANCE] Deferring character visual extraction for Chapter 1 to background")
                
                # Create a deferred task factory for character visual extraction (same pattern as other chapters)
                def create_visual_extraction_task():
                    task = asyncio.create_task(_update_character_visuals_background(new_chapter, state, state_manager))
                    state.pending_summary_tasks.append(task)  # Reuse existing task tracking
                    
                    # Add error visibility callback
                    def _log_visual_task_error(task: asyncio.Task) -> None:
                        if task.exception():
                            logger.error(f"Chapter 1 visual extraction task crashed: {task.exception()}")
                    
                    task.add_done_callback(_log_visual_task_error)
                    logger.info("[PERFORMANCE] Chapter 1 visual extraction task started in background after streaming completed")
                    return task
                
                # Store the deferred visual extraction task
                state.deferred_summary_tasks.append(create_visual_extraction_task)
                logger.info("[PERFORMANCE] Chapter 1 visual extraction task deferred for Chapter 1")
            except Exception as e:
                logger.error(f"Error setting up deferred character visual extraction for Chapter 1: {e}")
                # Continue with the story flow even if visual extraction setup fails

        # No need to process previous chapter for start choice
        is_story_complete = False
        
        # Return with flag indicating content was already streamed live
        return chapter_content, sampled_question, is_story_complete, True
        
    except Exception as e:
        logger.error(f"[PERFORMANCE] Live streaming failed for Chapter 1, falling back to traditional method: {e}")
        
        # Fallback to original blocking method
        chapter_content, sampled_question = await generate_chapter(
            story_category, lesson_topic, state
        )

        # Create and append new chapter
        new_chapter = await create_and_append_chapter(
            chapter_content, chapter_type, sampled_question, state_manager, None
        )

        if new_chapter:
            # Extract character visuals immediately (fallback behavior)
            try:
                logger.info("\nExtracting character visuals from Chapter 1 content (fallback)")
                updated_visuals = await _update_character_visuals(
                    state, new_chapter.content, state_manager
                )

                if updated_visuals:
                    logger.info(
                        f"Successfully extracted {len(updated_visuals)} character visuals from first chapter"
                    )
                else:
                    logger.warning(
                        "Character visual extraction from first chapter returned no results"
                    )
            except Exception as e:
                logger.error(
                    f"Error during character visual extraction from first chapter: {e}"
                )
                # Continue with the story flow even if visual extraction fails

        # No need to process previous chapter for start choice
        is_story_complete = False

        return chapter_content, sampled_question, is_story_complete, False


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
    # Handle first chapter agency choice
    if (
        previous_chapter.chapter_number == 1
        and previous_chapter.chapter_type == ChapterType.STORY
    ):
        logger.debug("Processing first chapter agency choice")

        # Extract agency category and visual details
        agency_category = ""
        visual_details = ""
        full_option_text = ""

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

                        # Store the full option text with visual details
                        full_option_text = option
                        break
                if visual_details:
                    break
        except Exception as e:
            logger.error(f"Error extracting agency details: {e}")

        # If we found the full option text, use it to create an enhanced choice text with visual details
        enhanced_choice_text = choice_text
        if full_option_text:
            # Extract the agency name and description parts
            agency_parts = choice_text.split("-", 1)
            if len(agency_parts) == 2:
                agency_name = agency_parts[0].strip()
                agency_description = agency_parts[1].strip()

                # Extract the visual details part from the full option
                visual_part = ""
                match = re.search(r"\[(.*?)\]", full_option_text)
                if match:
                    visual_part = f" [{match.group(1)}]"

                # Reconstruct the choice text with visual details
            enhanced_choice_text = f"{agency_name}{visual_part} - {agency_description}"

        # --- Start: Extract Agency Name ---
        extracted_name = "Unknown Agency"  # Default value
        try:
            # Split at " - " to separate name part from description
            name_part = choice_text.split(" - ", 1)[0]
            # Check for category prefix (e.g., "Category: Name")
            if ":" in name_part:
                extracted_name = name_part.split(":", 1)[1].strip()
            else:
                extracted_name = name_part.strip()
            logger.debug(f"Extracted agency name: {extracted_name}")
        except Exception as name_ex:
            logger.error(
                f"Error extracting agency name from '{choice_text}': {name_ex}"
            )
        # --- End: Extract Agency Name ---

        # Create the story response with the enhanced choice text
        story_response = StoryResponse(
            chosen_path=chosen_path, choice_text=enhanced_choice_text
        )
        previous_chapter.response = story_response
        logger.debug(
            f"Created story response with enhanced choice text: {story_response}"
        )

        # Store agency choice in metadata with visual details
        state.metadata["agency"] = {
            "type": "choice",
            "name": extracted_name,  # Use the extracted name
            "description": choice_text,  # Keep original full text as description
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
        logger.debug(f"Enhanced choice text with visuals: {enhanced_choice_text}")
        logger.debug(f"Agency category: {agency_category}")
        logger.debug(f"Visual details: {visual_details}")
    else:
        # For non-first chapters, process normally
        story_response = StoryResponse(chosen_path=chosen_path, choice_text=choice_text)
        previous_chapter.response = story_response
        logger.debug(f"Created story response: {story_response}")


async def _store_summary_safe(
    prev_chapter: ChapterData,
    state: AdventureState,
    title: str,
    summary_text: str
) -> None:
    """
    Safely write the summary/title to the shared state object.
    Uses a lock to avoid races with other summary tasks.
    """
    async with state.summary_lock:
        chap_idx = prev_chapter.chapter_number - 1
        
        # Pad lists if needed
        while len(state.chapter_summaries) <= chap_idx:
            state.chapter_summaries.append("Chapter summary not available")
            if hasattr(state, "summary_chapter_titles"):
                state.summary_chapter_titles.append(f"Chapter {len(state.summary_chapter_titles)+1}")
        
        # Store the actual summary and title
        state.chapter_summaries[chap_idx] = summary_text
        if hasattr(state, "summary_chapter_titles"):
            state.summary_chapter_titles[chap_idx] = title
        
        logger.info(f"Stored summary for chapter {prev_chapter.chapter_number}: {summary_text}")
        if hasattr(state, "summary_chapter_titles"):
            logger.info(f"Stored title for chapter {prev_chapter.chapter_number}: {title}")


async def _update_character_visuals_background(
    previous_chapter: ChapterData, state: AdventureState, state_manager: AdventureStateManager
) -> None:
    """Background task wrapper for character visual extraction with error handling."""
    try:
        logger.info(f"[PERFORMANCE] Starting background character visual extraction for chapter {previous_chapter.chapter_number}")
        
        updated_visuals = await _update_character_visuals(
            state, previous_chapter.content, state_manager
        )
        
        if updated_visuals:
            logger.info(f"[PERFORMANCE] Successfully extracted {len(updated_visuals)} character visuals in background")
        else:
            logger.warning(f"[PERFORMANCE] Character visual extraction returned no results for chapter {previous_chapter.chapter_number}")
            
    except Exception as e:
        logger.error(f"[PERFORMANCE] Background character visual extraction failed for chapter {previous_chapter.chapter_number}: {e}")
        # Continue execution - don't let visual extraction failures affect story flow


async def generate_chapter_summary_background(
    previous_chapter: ChapterData, state: AdventureState
) -> None:
    """Background task wrapper for chapter summary generation with error handling."""
    try:
        logger.info(f"[PERFORMANCE] Starting background chapter summary generation for chapter {previous_chapter.chapter_number}")
        
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

        await _store_summary_safe(previous_chapter, state, title, summary_text)
        
        logger.info(f"[PERFORMANCE] Completed background chapter summary generation for chapter {previous_chapter.chapter_number}")
    except Exception as e:
        logger.error(f"Background chapter summary generation failed for chapter {previous_chapter.chapter_number}: {e}")
        # Ensure we have a fallback summary to prevent summary screen issues
        async with state.summary_lock:
            if len(state.chapter_summaries) < previous_chapter.chapter_number:
                state.chapter_summaries.append("Chapter summary not available")
                if hasattr(state, "summary_chapter_titles"):
                    state.summary_chapter_titles.append(f"Chapter {previous_chapter.chapter_number}")
        # Continue execution - don't let summary failures affect story flow


async def generate_chapter_summary(
    previous_chapter: ChapterData, state: AdventureState
) -> None:
    """Generate a summary for the previous chapter (synchronous version for compatibility)."""
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
