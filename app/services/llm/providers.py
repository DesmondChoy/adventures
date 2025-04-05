from typing import Any, Dict, Optional, List, AsyncGenerator
import os
from openai import AsyncOpenAI
import google.generativeai as genai
from app.models.story import AdventureState, ChapterType
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_engineering import build_prompt
from app.services.llm.paragraph_formatter import (
    needs_paragraphing,
    reformat_text_with_paragraphs,
)
import logging

logger = logging.getLogger("story_app")


class OpenAIService(BaseLLMService):
    """OpenAI implementation of the LLM service."""

    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY is not set in environment variables!")

    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate content with custom system and user prompts as a stream of chunks."""
        # Log the prompts
        logger.info(
            "LLM Custom Prompt Request",
            extra={"llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}"},
        )

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Slightly lower temperature for more factual content
                stream=True,
            )

            # First, collect a buffer to check if paragraphing is needed
            buffer_size = 1000  # Characters to check for paragraph formatting
            collected_text = ""
            full_response = ""  # Track the full response regardless of streaming
            buffer_complete = False
            needs_formatting = False

            # Phase 1: Collect initial buffer to check formatting
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content  # Always track full response
                    collected_text += content

                    # Once we have enough text, check if it needs paragraphing
                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)

                        # If no formatting needed, start yielding the buffer
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""  # Reset after yielding
                        # If formatting needed, continue collecting without yielding

                    # If buffer check is complete and no formatting needed, stream normally
                    elif buffer_complete and not needs_formatting:
                        yield content

            # Phase 2: If formatting is needed, regenerate with the original prompt
            if needs_formatting:
                logger.info(
                    "Detected text without proper paragraph formatting, regenerating response..."
                )

                # Instead of reformatting, make a new call with the original prompt
                max_attempts = 3
                attempt = 0
                regenerated_text = None

                while attempt < max_attempts:
                    attempt += 1
                    logger.info(f"Regeneration attempt {attempt}/{max_attempts}")

                    try:
                        # Create a new non-streaming request with the same prompts
                        retry_response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.7,  # Slightly lower temperature for more factual content
                            stream=False,  # Non-streaming for regeneration
                        )

                        regenerated_text = retry_response.choices[0].message.content

                        # Check if it has proper paragraph formatting
                        if "\n\n" in regenerated_text:
                            logger.info(
                                f"Successfully generated text with proper paragraphs (attempt {attempt})"
                            )
                            break
                        else:
                            logger.warning(
                                f"Regeneration attempt {attempt} still lacks paragraph breaks"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error in regeneration attempt {attempt}: {str(e)}"
                        )

                # Use the regenerated text if successful, otherwise fall back to the original
                if regenerated_text and "\n\n" in regenerated_text:
                    yield regenerated_text
                    logger.info("Sent regenerated text with proper paragraphing")
                    full_response = regenerated_text  # Update full response for logging
                else:
                    # If all regeneration attempts failed, fall back to reformatting
                    logger.warning(
                        f"All {max_attempts} regeneration attempts failed, falling back to reformatting"
                    )
                    reformatted_text = await reformat_text_with_paragraphs(
                        self, full_response
                    )
                    yield reformatted_text
                    logger.info("Sent reformatted text with paragraph formatting")
                    full_response = reformatted_text  # Update full response for logging

            # Log the complete response
            logger.info(
                "LLM Response",
                extra={"llm_response": full_response},
            )

        except Exception as e:
            logger.error(
                "LLM Request Failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                },
            )
            raise  # Re-raise the exception after logging

    async def generate_chapter_stream(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the chapter content (story or lesson) as a stream of chunks."""
        # Build prompts using the optimized prompt engineering module
        system_prompt, user_prompt = build_prompt(
            state=state,
            lesson_question=question,
            previous_lessons=previous_lessons,
            context=context,
        )

        # Log the prompts
        logger.info(
            "LLM Prompt Request",
            extra={"llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}"},
        )

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
                stream=True,
            )

            # First, collect a buffer to check if paragraphing is needed
            buffer_size = 1000  # Characters to check for paragraph formatting
            collected_text = ""
            full_response = ""  # Track the full response regardless of streaming
            buffer_complete = False
            needs_formatting = False

            # Phase 1: Collect initial buffer to check formatting
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content  # Always track full response
                    collected_text += content

                    # Once we have enough text, check if it needs paragraphing
                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)

                        # If no formatting needed, start yielding the buffer
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""  # Reset after yielding
                        # If formatting needed, continue collecting without yielding

                    # If buffer check is complete and no formatting needed, stream normally
                    elif buffer_complete and not needs_formatting:
                        yield content

            # Phase 2: If formatting is needed, regenerate with the original prompt
            if needs_formatting:
                logger.info(
                    "Detected text without proper paragraph formatting, regenerating response..."
                )

                # Instead of reformatting, make a new call with the original prompt
                max_attempts = 3
                attempt = 0
                regenerated_text = None

                while attempt < max_attempts:
                    attempt += 1
                    logger.info(f"Regeneration attempt {attempt}/{max_attempts}")

                    try:
                        # Create a new non-streaming request with the same prompts
                        retry_response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.7,  # Slightly lower temperature for more factual content
                            stream=False,  # Non-streaming for regeneration
                        )

                        regenerated_text = retry_response.choices[0].message.content

                        # Check if it has proper paragraph formatting
                        if "\n\n" in regenerated_text:
                            logger.info(
                                f"Successfully generated text with proper paragraphs (attempt {attempt})"
                            )
                            break
                        else:
                            logger.warning(
                                f"Regeneration attempt {attempt} still lacks paragraph breaks"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error in regeneration attempt {attempt}: {str(e)}"
                        )

                # Use the regenerated text if successful, otherwise fall back to the original
                if regenerated_text and "\n\n" in regenerated_text:
                    yield regenerated_text
                    logger.info("Sent regenerated text with proper paragraphing")
                    full_response = regenerated_text  # Update full response for logging
                else:
                    # If all regeneration attempts failed, fall back to reformatting
                    logger.warning(
                        f"All {max_attempts} regeneration attempts failed, falling back to reformatting"
                    )
                    reformatted_text = await reformat_text_with_paragraphs(
                        self, full_response
                    )
                    yield reformatted_text
                    logger.info("Sent reformatted text with paragraph formatting")
                    full_response = reformatted_text  # Update full response for logging

            # Log the complete response
            logger.info(
                "LLM Response",
                extra={"llm_response": full_response},
            )

        except Exception as e:
            logger.error(
                "LLM Request Failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                },
            )
            raise  # Re-raise the exception after logging


class GeminiService(BaseLLMService):
    """Google Gemini implementation of the LLM service."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize Gemini service with the specified model."""
        self.model = model
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY is not set in environment variables!")
        genai.configure(api_key=api_key)
        # Initialize with system prompt as part of model configuration
        self.client = genai.GenerativeModel(
            model_name=self.model,
            generation_config=genai.GenerationConfig(
                temperature=0.9,
                max_output_tokens=8000,  # Adjust based on your needs
            ),
        )

    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate content with custom system and user prompts as a stream of chunks."""
        logger.info(
            "LLM Custom Prompt Request (Gemini)",
            extra={"llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}"},
        )

        try:
            # Initialize the model with system prompt
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt,
            )

            # Generate content with streaming
            response = model.generate_content(user_prompt, stream=True)

            # First, collect a buffer to check if paragraphing is needed
            buffer_size = 1000  # Characters to check for paragraph formatting
            collected_text = ""
            full_response = ""  # Track the full response regardless of streaming
            buffer_complete = False
            needs_formatting = False

            # Phase 1: Collect initial buffer to check formatting
            chunk_count = 0
            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    full_response += content  # Always track full response
                    collected_text += content
                    chunk_count += 1

                    # Once we have enough text, check if it needs paragraphing
                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)

                        # If no formatting needed, start yielding the buffer
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""  # Reset after yielding
                        # If formatting needed, continue collecting without yielding

                    # If buffer check is complete and no formatting needed, stream normally
                    elif buffer_complete and not needs_formatting:
                        yield content

            # Phase 2: If formatting is needed, regenerate with the original prompt
            if needs_formatting:
                logger.info(
                    "Detected text without proper paragraph formatting, regenerating response..."
                )

                # Instead of reformatting, make a new call with the original prompt
                max_attempts = 3
                attempt = 0
                regenerated_text = None

                while attempt < max_attempts:
                    attempt += 1
                    logger.info(f"Regeneration attempt {attempt}/{max_attempts}")

                    try:
                        # Re-initialize model to use the same system instruction
                        retry_model = genai.GenerativeModel(
                            model_name=self.model,
                            system_instruction=system_prompt,
                        )

                        # Generate new response
                        retry_response = retry_model.generate_content(user_prompt)
                        regenerated_text = retry_response.text

                        # Check if it has proper paragraph formatting
                        if "\n\n" in regenerated_text:
                            logger.info(
                                f"Successfully generated text with proper paragraphs (attempt {attempt})"
                            )
                            break
                        else:
                            logger.warning(
                                f"Regeneration attempt {attempt} still lacks paragraph breaks"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error in regeneration attempt {attempt}: {str(e)}"
                        )

                # Use the regenerated text if successful, otherwise fall back to the original
                if regenerated_text and "\n\n" in regenerated_text:
                    yield regenerated_text
                    logger.info("Sent regenerated text with proper paragraphing")
                    full_response = regenerated_text  # Update full response for logging
                else:
                    # If all regeneration attempts failed, fall back to reformatting
                    logger.warning(
                        f"All {max_attempts} regeneration attempts failed, falling back to reformatting"
                    )
                    reformatted_text = await reformat_text_with_paragraphs(
                        self, full_response
                    )
                    yield reformatted_text
                    logger.info("Sent reformatted text with paragraph formatting")
                    full_response = reformatted_text  # Update full response for logging

            # Log the complete response
            logger.info(
                "LLM Response (Gemini)",
                extra={"llm_response": full_response},
            )

        except Exception as e:
            logger.error(
                "LLM Request Failed (Gemini)",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                },
            )
            raise  # Re-raise the exception after logging

    async def generate_chapter_stream(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the chapter content (story or lesson) as a stream of chunks."""
        # Build prompts using the optimized prompt engineering module
        system_prompt, user_prompt = build_prompt(
            state=state,
            lesson_question=question,
            previous_lessons=previous_lessons,
            context=context,
        )

        # Log the prompts at INFO level
        logger.info("\n=== LLM Prompt Request (Gemini) ===")
        logger.info(f"System Prompt:\n{system_prompt}")
        logger.info(f"User Prompt:\n{user_prompt}")
        logger.info("========================\n")

        try:
            # Initialize the model with system prompt
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt,
            )

            # Generate content with streaming
            response = model.generate_content(user_prompt, stream=True)

            # First, collect a buffer to check if paragraphing is needed
            buffer_size = 1000  # Characters to check for paragraph formatting
            collected_text = ""
            full_response = ""  # Track the full response regardless of streaming
            buffer_complete = False
            needs_formatting = False

            # Phase 1: Collect initial buffer to check formatting
            chunk_count = 0
            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    full_response += content  # Always track full response
                    collected_text += content
                    chunk_count += 1

                    # Once we have enough text, check if it needs paragraphing
                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)

                        # If no formatting needed, start yielding the buffer
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""  # Reset after yielding
                        # If formatting needed, continue collecting without yielding

                    # If buffer check is complete and no formatting needed, stream normally
                    elif buffer_complete and not needs_formatting:
                        yield content

            # Phase 2: If formatting is needed, reformat and yield the complete text
            if needs_formatting:
                logger.info(
                    "Detected text without proper paragraph formatting, reformatting..."
                )
                reformatted_text = await reformat_text_with_paragraphs(
                    self, full_response
                )
                yield reformatted_text
                logger.info("Sent reformatted text with proper paragraphing")

            # Log the complete response
            logger.info("\n=== LLM Response ===")
            logger.info(reformatted_text if needs_formatting else full_response)
            logger.info("========================\n")

        except Exception as e:
            logger.error("\n=== ERROR: LLM Request Failed ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("===============================\n")
            raise  # Re-raise the exception after logging
