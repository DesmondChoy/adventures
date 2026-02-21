from typing import Any, Dict, Optional, List, AsyncGenerator
import os
from openai import AsyncOpenAI
from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig
from app.models.story import AdventureState
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_engineering import build_prompt
from app.services.llm.paragraph_formatter import (
    needs_paragraphing,
    regenerate_with_paragraphs,
)
import logging

logger = logging.getLogger("story_app")


# Centralized Model Configuration
class ModelConfig:
    """Centralized configuration for LLM models and their settings."""

    # Gemini Models
    GEMINI_MODEL = "gemini-2.5-flash"  # Default for backward compatibility
    GEMINI_FLASH_MODEL = "gemini-2.5-flash"
    GEMINI_FLASH_LITE_MODEL = "gemini-2.5-flash-lite"  # Cost-optimized model
    GEMINI_THINKING_BUDGET = 512

    # OpenAI Models
    OPENAI_MODEL = "gpt-4o-2024-08-06"

    # Usage-specific model assignments
    STORY_GENERATION_MODEL = GEMINI_FLASH_MODEL
    IMAGE_SCENE_MODEL = GEMINI_FLASH_MODEL
    SUMMARY_MODEL = GEMINI_FLASH_LITE_MODEL
    PARAGRAPH_FORMAT_MODEL = GEMINI_FLASH_LITE_MODEL
    CHARACTER_VISUAL_MODEL = GEMINI_FLASH_LITE_MODEL
    CHAPTER_SUMMARY_MODEL = GEMINI_FLASH_LITE_MODEL
    IMAGE_PROMPT_MODEL = GEMINI_FLASH_LITE_MODEL

    @classmethod
    def get_gemini_config(cls) -> GenerateContentConfig:
        """Get Gemini configuration with thinking budget."""
        return GenerateContentConfig(
            thinking_config=ThinkingConfig(thinking_budget=cls.GEMINI_THINKING_BUDGET)
        )


class OpenAIService(BaseLLMService):
    """OpenAI implementation of the LLM service."""

    def __init__(self, model: str = ModelConfig.OPENAI_MODEL):
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY is not set in environment variables!")

    async def generate_character_visuals_json(
        self,
        custom_prompt: str,
    ) -> str:
        """Generate character visuals JSON with direct response (no streaming).

        This method is specifically for character visual extraction where we need
        the complete response before processing. It avoids streaming to ensure
        we get a complete JSON response.

        Args:
            custom_prompt: The prompt to send to the LLM

        Returns:
            str: Complete response text from the LLM
        """
        # For OpenAI we'll use a simple system prompt
        system_prompt = (
            "You are a visual detail extractor for a storytelling application."
        )
        user_prompt = custom_prompt

        logger.debug("CHARACTER VISUAL JSON REQUEST (OpenAI)")

        try:
            # Generate complete response in one call (no streaming)
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                stream=False,  # NO STREAMING for this specific use case
            )

            # Extract the text
            response_text = completion.choices[0].message.content

            # logger.info("\n=== CHARACTER VISUAL JSON RESPONSE ===")
            # logger.info(f"Response excerpt:\n{response_text[:300]}...")
            # logger.info(f"Response length: {len(response_text)} characters")
            # logger.info("========================\n")

            return response_text

        except Exception as e:
            logger.error(f"Error generating character visuals JSON (OpenAI): {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return ""  # Return empty string on error

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

            # Collect buffer to check if paragraphing is needed
            buffer_size = 400
            collected_text = ""
            full_response = ""
            buffer_complete = False
            needs_formatting = False

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    collected_text += content

                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""
                    elif buffer_complete and not needs_formatting:
                        yield content

            if needs_formatting:
                async def _regenerate():
                    resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                        stream=False,
                    )
                    return resp.choices[0].message.content

                result = await regenerate_with_paragraphs(
                    full_response, _regenerate, llm_service=self
                )
                yield result
                full_response = result

            logger.info("LLM Response", extra={"llm_response": full_response})

        except Exception as e:
            logger.error(
                "LLM Request Failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                },
            )
            raise

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

            # Collect buffer to check if paragraphing is needed
            buffer_size = 400
            collected_text = ""
            full_response = ""
            buffer_complete = False
            needs_formatting = False

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    collected_text += content

                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""
                    elif buffer_complete and not needs_formatting:
                        yield content

            if needs_formatting:
                async def _regenerate():
                    resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                        stream=False,
                    )
                    return resp.choices[0].message.content

                result = await regenerate_with_paragraphs(
                    full_response, _regenerate, llm_service=self
                )
                yield result
                full_response = result

            logger.info("LLM Response", extra={"llm_response": full_response})

        except Exception as e:
            logger.error(
                "LLM Request Failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                },
            )
            raise


class GeminiService(BaseLLMService):
    """Google Gemini implementation of the LLM service."""

    def __init__(self, model: str = ModelConfig.GEMINI_MODEL):
        """Initialize Gemini service with the specified model."""
        self.model = model
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY is not set in environment variables!")
        # Initialize with new google-genai client
        self.client = genai.Client(api_key=api_key)

    async def generate_character_visuals_json(
        self,
        custom_prompt: str,
    ) -> str:
        """Generate character visuals JSON with direct response (no streaming).

        This method is specifically for character visual extraction where we need
        the complete response before processing. It avoids streaming to ensure
        we get a complete JSON response.

        Args:
            custom_prompt: The prompt to send to the LLM

        Returns:
            str: Complete response text from the LLM
        """
        # For Gemini we'll use a simple system prompt
        system_prompt = (
            "You are a visual detail extractor for a storytelling application."
        )
        user_prompt = custom_prompt

        logger.debug("CHARACTER VISUAL JSON REQUEST (Gemini)")

        try:
            # Generate complete response in one call (no streaming) using new API
            # Combine system and user prompts as the new API handles system instruction differently
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.client.models.generate_content(
                model=self.model,
                contents=combined_prompt,
                config=ModelConfig.get_gemini_config(),
            )

            # Extract the text
            response_text = response.text

            # logger.info("\n=== CHARACTER VISUAL JSON RESPONSE ===")
            # logger.info(f"Response excerpt:\n{response_text[:300]}...")
            # logger.info(f"Response length: {len(response_text)} characters")
            # logger.info("========================\n")

            return response_text

        except Exception as e:
            logger.error(f"Error generating character visuals JSON: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return ""  # Return empty string on error

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
            # Generate content with streaming using new API
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.client.models.generate_content_stream(
                model=self.model,
                contents=combined_prompt,
                config=ModelConfig.get_gemini_config(),
            )

            # Collect buffer to check if paragraphing is needed
            buffer_size = 400
            collected_text = ""
            full_response = ""
            buffer_complete = False
            needs_formatting = False

            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    full_response += content
                    collected_text += content

                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""
                    elif buffer_complete and not needs_formatting:
                        yield content

            if needs_formatting:
                async def _regenerate():
                    cp = f"{system_prompt}\n\n{user_prompt}"
                    retry_resp = self.client.models.generate_content(
                        model=self.model,
                        contents=cp,
                        config=ModelConfig.get_gemini_config(),
                    )
                    return retry_resp.text

                result = await regenerate_with_paragraphs(
                    full_response, _regenerate, llm_service=self
                )
                yield result
                full_response = result

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
            raise

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
            # Generate content with streaming using new API
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.client.models.generate_content_stream(
                model=self.model,
                contents=combined_prompt,
                config=ModelConfig.get_gemini_config(),
            )

            # Collect buffer to check if paragraphing is needed
            buffer_size = 400
            collected_text = ""
            full_response = ""
            buffer_complete = False
            needs_formatting = False

            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    full_response += content
                    collected_text += content

                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""
                    elif buffer_complete and not needs_formatting:
                        yield content

            if needs_formatting:
                async def _regenerate():
                    cp = f"{system_prompt}\n\n{user_prompt}"
                    retry_resp = self.client.models.generate_content(
                        model=self.model,
                        contents=cp,
                        config=ModelConfig.get_gemini_config(),
                    )
                    return retry_resp.text

                result = await regenerate_with_paragraphs(
                    full_response, _regenerate, llm_service=self
                )
                yield result
                full_response = result

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
                },
            )
            raise
