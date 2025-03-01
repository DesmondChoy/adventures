from typing import Any, Dict, Optional, List, AsyncGenerator
import os
from openai import AsyncOpenAI
import google.generativeai as genai
from app.models.story import AdventureState, ChapterType
from app.services.llm.base import BaseLLMService
from app.services.llm.prompt_engineering import (
    build_system_prompt,
    build_user_prompt,
    _build_base_prompt,
)
from app.services.llm.streamlined_prompt_engineering import build_streamlined_prompt
from app.services.llm.further_streamlined_prompt_engineering import (
    build_further_streamlined_prompt,
)
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("story_app")


class OpenAIService(BaseLLMService):
    """OpenAI implementation of the LLM service."""

    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        self.model = model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY is not set in environment variables!")

    async def generate_chapter_stream(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the chapter content (story or lesson) as a stream of chunks."""
        # For the first chapter, use the further streamlined prompts
        if (
            state.current_chapter_number == 1
            and state.planned_chapter_types[0] == ChapterType.STORY
        ):
            logger.info("Using further streamlined prompts for first chapter")
            system_prompt, user_prompt = build_further_streamlined_prompt(
                state, question, previous_lessons
            )
        else:
            # For other chapters, use the original prompts
            logger.info(
                f"Using original prompts for chapter {state.current_chapter_number}"
            )

            # Get base prompt components
            base_prompt, story_phase, chapter_type = _build_base_prompt(state)

            # Get number of previous lessons
            num_previous_lessons = len(previous_lessons) if previous_lessons else 0

            # Get consequences guidance if there are previous lessons
            consequences_guidance = ""
            if previous_lessons and len(previous_lessons) > 0:
                from app.services.llm.prompt_engineering import process_consequences

                last_lesson = previous_lessons[-1]
                consequences_guidance = process_consequences(
                    last_lesson.is_correct,
                    last_lesson.question,
                    last_lesson.chosen_answer,
                    state.current_chapter_number,
                )

            # Build prompts using the original prompt engineering module
            system_prompt = build_system_prompt(state)
            user_prompt = build_user_prompt(
                state=state,
                lesson_question=question,
                previous_lessons=previous_lessons,
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

            collected_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    collected_response += content
                    yield content

            # Log the complete response after streaming
            logger.info("LLM Response", extra={"llm_response": collected_response})

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

    async def generate_chapter_stream(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the chapter content (story or lesson) as a stream of chunks."""
        # For the first chapter, use the further streamlined prompts
        if (
            state.current_chapter_number == 1
            and state.planned_chapter_types[0] == ChapterType.STORY
        ):
            print(
                "\n=== DEBUG: Using further streamlined prompts for first chapter ==="
            )
            system_prompt, user_prompt = build_further_streamlined_prompt(
                state, question, previous_lessons
            )
        else:
            # For other chapters, use the original prompts
            print(
                f"\n=== DEBUG: Using original prompts for chapter {state.current_chapter_number} ==="
            )

            # Get base prompt components
            base_prompt, story_phase, chapter_type = _build_base_prompt(state)

            # Get number of previous lessons
            num_previous_lessons = len(previous_lessons) if previous_lessons else 0

            # Get consequences guidance if there are previous lessons
            consequences_guidance = ""
            if previous_lessons and len(previous_lessons) > 0:
                from app.services.llm.prompt_engineering import process_consequences

                last_lesson = previous_lessons[-1]
                consequences_guidance = process_consequences(
                    last_lesson.is_correct,
                    last_lesson.question,
                    last_lesson.chosen_answer,
                    state.current_chapter_number,
                )

            # Build prompts using the original prompt engineering module
            system_prompt = build_system_prompt(state)
            user_prompt = build_user_prompt(
                state=state,
                lesson_question=question,
                previous_lessons=previous_lessons,
            )

        print("\n=== DEBUG: LLM Prompt Request ===")
        print("System Prompt:")
        print(system_prompt)
        print("\nUser Prompt:")
        print(user_prompt)
        print("========================\n")

        try:
            # Initialize the model with system prompt
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt,
            )

            # Generate content with streaming
            response = model.generate_content(user_prompt, stream=True)

            collected_response = ""
            for chunk in response:
                if chunk.text:
                    collected_response += chunk.text
                    yield chunk.text

            # Log the complete response after streaming
            print("\n=== DEBUG: LLM Response ===")
            print(collected_response)
            print("========================\n")

        except Exception as e:
            print("\n=== ERROR: LLM Request Failed ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============================\n")
            raise  # Re-raise the exception after logging
