"""
Paragraph formatting utilities for LLM responses.

This module provides functions to detect and fix text that lacks proper paragraph formatting.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger("story_app")


def needs_paragraphing(text: str) -> bool:
    """
    Detect if text needs paragraph formatting.

    Args:
        text: The text to check

    Returns:
        bool: True if the text needs paragraph formatting, False otherwise
    """
    # Check if text is substantial in length (at least 200 chars)
    if len(text) < 200:
        return False

    # Check if text already has paragraph breaks
    if "\n\n" in text:
        return False

    # Count sentences (approximation)
    sentence_count = len(re.findall(r"[.!?]\s+[A-Z]", text))

    # If there are multiple sentences but no paragraph breaks, formatting is needed
    if sentence_count > 3:
        return True

    # Check for dialogue indicators without proper formatting
    dialogue_markers = len(re.findall(r'["\'"].+?["\']', text))
    if dialogue_markers > 2:
        return True

    return False


async def reformat_text_with_paragraphs(
    text: str, max_attempts: int = 3, llm_service=None
) -> str:
    """
    Reformat text with proper paragraph breaks using a lightweight LLM service.
    Will make multiple attempts if needed.

    Args:
        text: The text to reformat
        max_attempts: Maximum number of formatting attempts (default: 3)
        llm_service: Optional LLM service, defaults to Flash Lite service

    Returns:
        str: The reformatted text with proper paragraph breaks
    """
    # Skip reformatting if text doesn't need it
    if not needs_paragraphing(text):
        return text

    # Use Flash Lite service if none provided
    if llm_service is None:
        from app.services.llm.factory import LLMServiceFactory
        llm_service = LLMServiceFactory.create_for_use_case("paragraph_formatting")

    logger.info("Reformatting text with paragraphs")

    current_text = text

    # Try reformatting up to max_attempts times
    for attempt in range(max_attempts):
        try:
            # Create the instructions based on attempt number
            basic_instruction = ""
            important_instruction = "IMPORTANT: Make sure to include blank lines (double line breaks) between paragraphs."
            very_important_instruction = "This is VERY IMPORTANT: Each paragraph must be separated by a blank line. Use double line breaks (\\n\\n) between paragraphs."

            first_instruction = (
                basic_instruction if attempt == 0 else important_instruction
            )
            second_instruction = (
                basic_instruction if attempt < 2 else very_important_instruction
            )

            # Then use them in the f-string
            prompt = f"""
            The following text needs proper paragraph formatting. Please reformat it with appropriate paragraph breaks
            while preserving all original content and meaning. Add paragraph breaks where natural pauses occur,
            such as between different speakers, scene transitions, or changes in focus.
            {first_instruction}
            {second_instruction}
            
            TEXT: {current_text}
            
            REFORMATTED TEXT WITH PARAGRAPHS:
            """

            # Log the full reformatting prompt
            logger.info(
                f"Paragraph reformatting attempt {attempt + 1}/{max_attempts}",
                extra={
                    "reformatting_prompt": prompt,
                    "service_type": llm_service.__class__.__name__,
                    "temperature": 0.3 if attempt == 0 else 0.7,
                },
            )

            # Use the standard LLM service interface
            system_prompt = "You are a helpful assistant that reformats text with proper paragraph breaks."
            
            # Collect the complete response from the streaming interface
            reformatted_text = ""
            response_generator = await llm_service.generate_with_prompt(
                system_prompt=system_prompt,
                user_prompt=prompt
            )
            async for chunk in response_generator:
                reformatted_text += chunk

            # Log the reformatted response
            logger.info(
                f"Received reformatted text (attempt {attempt + 1}/{max_attempts})",
                extra={
                    "reformatted_text": reformatted_text[:100] + "..."
                    if len(reformatted_text) > 100
                    else reformatted_text,
                    "has_paragraph_breaks": "\n\n" in reformatted_text,
                    "length": len(reformatted_text),
                },
            )

            # Check if reformatting was successful
            if "\n\n" in reformatted_text:
                logger.info(
                    f"Successfully reformatted text with paragraphs (attempt {attempt + 1})"
                )
                return reformatted_text

            logger.warning(
                f"Reformatting attempt {attempt + 1} failed to add paragraph breaks, trying again..."
            )

            # For subsequent attempts, use the most recent reformatted text
            # This might help if the LLM has made some improvements but not enough
            current_text = reformatted_text

        except Exception as e:
            logger.error(f"Error in reformatting attempt {attempt + 1}: {str(e)}")
            # Continue to next attempt rather than failing immediately

    # If we've exhausted all attempts and still don't have proper formatting
    logger.warning(
        f"All {max_attempts} reformatting attempts failed, returning original text"
    )
    return text


async def collect_and_check_formatting(
    stream_generator, buffer_size: int = 1000
) -> Tuple[str, bool]:
    """
    Collect text from a stream generator and check if it needs formatting.

    Args:
        stream_generator: The stream generator to collect text from
        buffer_size: The size of the buffer to collect before checking

    Returns:
        Tuple[str, bool]: The collected text and whether it needs formatting
    """
    collected_text = ""
    needs_formatting = False

    # Collect initial buffer
    try:
        async for chunk in stream_generator:
            collected_text += chunk
            if len(collected_text) >= buffer_size:
                break
    except Exception as e:
        logger.error(f"Error collecting text from stream: {str(e)}")
        return collected_text, False

    # Check if the collected text needs formatting
    needs_formatting = needs_paragraphing(collected_text)

    return collected_text, needs_formatting
