from typing import Any, Dict, Optional, List, AsyncGenerator
import hashlib
import os
from openai import AsyncOpenAI
from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig
from app.models.story import AdventureState, ChapterType
from app.services.llm.base import BaseLLMService
from app.services.llm.chapter_output import (
    GeneratedChapter,
    NarrativeChapterResponse,
    StoryChapterResponse,
)
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

    # Gemini model retained for summaries and other lightweight support tasks.
    GEMINI_FLASH_LITE_MODEL = "gemini-2.5-flash-lite"  # Cost-optimized model
    GEMINI_FLASH_LITE_THINKING_BUDGET = 512

    # OpenAI model used for narrative and image-scene text generation.
    OPENAI_MODEL = "gpt-5.6-luna"
    OPENAI_REASONING_EFFORT = "low"
    OPENAI_MAX_OUTPUT_TOKENS = 8192

    # Usage-specific model assignments
    STORY_GENERATION_MODEL = OPENAI_MODEL
    IMAGE_SCENE_MODEL = OPENAI_MODEL
    SUMMARY_MODEL = GEMINI_FLASH_LITE_MODEL
    PARAGRAPH_FORMAT_MODEL = GEMINI_FLASH_LITE_MODEL
    CHARACTER_VISUAL_MODEL = GEMINI_FLASH_LITE_MODEL
    CHAPTER_SUMMARY_MODEL = GEMINI_FLASH_LITE_MODEL
    IMAGE_PROMPT_MODEL = GEMINI_FLASH_LITE_MODEL

    @classmethod
    def get_gemini_config(cls) -> GenerateContentConfig:
        """Get Gemini configuration with thinking budget."""
        return GenerateContentConfig(
            thinking_config=ThinkingConfig(
                thinking_budget=cls.GEMINI_FLASH_LITE_THINKING_BUDGET
            )
        )


class OpenAIService(BaseLLMService):
    """OpenAI Responses API implementation for narrative generation."""

    def __init__(self, model: str = ModelConfig.OPENAI_MODEL):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for story generation")
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    @staticmethod
    def _safety_identifier(state: AdventureState) -> Optional[str]:
        """Return a stable privacy-preserving identifier when state provides one."""
        metadata = getattr(state, "metadata", {})
        raw_identifier = metadata.get("user_id") or metadata.get("client_uuid")
        if not raw_identifier:
            return None
        return hashlib.sha256(str(raw_identifier).encode("utf-8")).hexdigest()

    @staticmethod
    def _refusal_text(response: Any) -> Optional[str]:
        for output in getattr(response, "output", []):
            for content in getattr(output, "content", []):
                if getattr(content, "type", None) == "refusal":
                    return getattr(content, "refusal", "Model refused the request")
        return None

    @staticmethod
    def _ensure_completed(response: Any) -> None:
        if getattr(response, "status", None) == "completed":
            return
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None) or getattr(
            response, "error", None
        )
        raise ValueError(
            f"OpenAI response did not complete successfully: "
            f"status={getattr(response, 'status', 'unknown')}, reason={reason}"
        )

    def _log_response_metadata(self, response: Any, use_case: str) -> None:
        usage = getattr(response, "usage", None)
        logger.info(
            "OpenAI Responses API completed",
            extra={
                "llm_provider": "openai",
                "llm_model": self.model,
                "llm_use_case": use_case,
                "llm_response_id": getattr(response, "id", None),
                "llm_request_id": getattr(response, "_request_id", None),
                "llm_status": getattr(response, "status", None),
                "llm_usage": usage.model_dump() if usage else None,
            },
        )

    async def _generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        use_case: str,
    ) -> str:
        response = await self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": ModelConfig.OPENAI_REASONING_EFFORT},
            max_output_tokens=ModelConfig.OPENAI_MAX_OUTPUT_TOKENS,
            store=False,
        )
        self._log_response_metadata(response, use_case)
        self._ensure_completed(response)
        response_text = response.output_text
        if not response_text.strip():
            refusal = self._refusal_text(response)
            raise ValueError(refusal or "OpenAI response contained no text")
        return response_text

    async def generate_structured_chapter(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedChapter:
        """Generate and validate one chapter with Responses Structured Outputs."""
        del story_config
        system_prompt, user_prompt = build_prompt(
            state=state,
            lesson_question=question,
            previous_lessons=previous_lessons,
            context=context,
        )
        chapter_type = state.planned_chapter_types[state.current_chapter_number - 1]
        if not isinstance(chapter_type, ChapterType):
            chapter_type = ChapterType(chapter_type)
        response_format = (
            StoryChapterResponse
            if chapter_type in (ChapterType.STORY, ChapterType.REFLECT)
            else NarrativeChapterResponse
        )

        request: Dict[str, Any] = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "reasoning": {"effort": ModelConfig.OPENAI_REASONING_EFFORT},
            "text_format": response_format,
            "max_output_tokens": ModelConfig.OPENAI_MAX_OUTPUT_TOKENS,
            "store": False,
        }
        safety_identifier = self._safety_identifier(state)
        if safety_identifier:
            request["safety_identifier"] = safety_identifier

        logger.info(
            "OpenAI structured chapter request",
            extra={
                "llm_provider": "openai",
                "llm_model": self.model,
                "llm_reasoning_effort": ModelConfig.OPENAI_REASONING_EFFORT,
                "chapter_number": state.current_chapter_number,
                "chapter_type": chapter_type.value,
                "llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
            },
        )

        response = await self.client.responses.parse(**request)
        self._log_response_metadata(response, "story_generation")
        self._ensure_completed(response)
        parsed = response.output_parsed
        if parsed is None:
            refusal = self._refusal_text(response)
            raise ValueError(refusal or "OpenAI structured response could not be parsed")

        if isinstance(parsed, StoryChapterResponse):
            result = GeneratedChapter(
                content=parsed.content,
                choices=tuple(parsed.choices),
            )
        else:
            result = GeneratedChapter(content=parsed.content)

        logger.info(
            "OpenAI structured chapter validated",
            extra={
                "chapter_number": state.current_chapter_number,
                "chapter_type": chapter_type.value,
                "choice_count": len(result.choices),
                "llm_response": result.content,
            },
        )
        return result

    async def generate_character_visuals_json(self, custom_prompt: str) -> str:
        """Generate a complete visual-description response."""
        return await self._generate_text(
            "You are a visual detail extractor for a storytelling application.",
            custom_prompt,
            use_case="character_visuals",
        )

    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate custom text through Responses and yield the validated result."""
        logger.info(
            "LLM Custom Prompt Request",
            extra={"llm_prompt": f"System: {system_prompt}\n\nUser: {user_prompt}"},
        )
        try:
            result = await self._generate_text(
                system_prompt,
                user_prompt,
                use_case="custom_prompt",
            )
            skip_paragraph_formatting = bool(
                context and context.get("skip_paragraph_formatting")
            )
            if not skip_paragraph_formatting and needs_paragraphing(result):

                async def _regenerate():
                    return await self._generate_text(
                        system_prompt,
                        user_prompt,
                        use_case="custom_prompt_paragraph_retry",
                    )

                result = await regenerate_with_paragraphs(result, _regenerate, self)
            yield result
            logger.info("LLM Response", extra={"llm_response": result})

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
        """Generate free text for non-story support use cases through Responses."""
        system_prompt, user_prompt = build_prompt(
            state=state,
            lesson_question=question,
            previous_lessons=previous_lessons,
            context=context,
        )

        async for chunk in self.generate_with_prompt(
            system_prompt,
            user_prompt,
            context=context,
        ):
            yield chunk


class GeminiService(BaseLLMService):
    """Gemini Flash Lite implementation for lightweight support tasks."""

    def __init__(self, model: str = ModelConfig.GEMINI_FLASH_LITE_MODEL):
        """Initialize the Gemini Flash Lite service."""
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
            response_text = response.text or ""

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
            skip_paragraph_formatting = bool(
                context and context.get("skip_paragraph_formatting")
            )

            for chunk in response:
                if chunk.text:
                    content = chunk.text
                    full_response += content
                    if skip_paragraph_formatting:
                        yield content
                        continue
                    collected_text += content

                    if not buffer_complete and len(collected_text) >= buffer_size:
                        buffer_complete = True
                        needs_formatting = needs_paragraphing(collected_text)
                        if not needs_formatting:
                            yield collected_text
                            collected_text = ""
                    elif buffer_complete and not needs_formatting:
                        yield content

            if not buffer_complete and collected_text:
                yield collected_text

            if needs_formatting:
                async def _regenerate():
                    cp = f"{system_prompt}\n\n{user_prompt}"
                    retry_resp = self.client.models.generate_content(
                        model=self.model,
                        contents=cp,
                        config=ModelConfig.get_gemini_config(),
                    )
                    return retry_resp.text or ""

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

            if not buffer_complete and collected_text:
                yield collected_text

            if needs_formatting:
                async def _regenerate():
                    cp = f"{system_prompt}\n\n{user_prompt}"
                    retry_resp = self.client.models.generate_content(
                        model=self.model,
                        contents=cp,
                        config=ModelConfig.get_gemini_config(),
                    )
                    return retry_resp.text or ""

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
