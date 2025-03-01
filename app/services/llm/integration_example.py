"""
Integration example for prompt engineering.

This module demonstrates how to integrate the prompt engineering functions
into the existing LLM service in the Learning Odyssey application.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from app.models.story import AdventureState, ChapterType
from app.services.llm.prompt_engineering import (
    build_prompt,
    build_system_prompt,
    build_user_prompt,
    LessonQuestion,
)


def generate_llm_prompts(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """Generate system and user prompts for LLM.

    This function demonstrates how to use the prompt engineering functions
    to generate prompts for the LLM service.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    logger = logging.getLogger("llm_service")

    # Use the build_prompt function to generate both system and user prompts
    logger.info(f"Generating prompts for chapter {state.current_chapter_number}")
    return build_prompt(state, lesson_question, previous_lessons)


# Example usage in an LLM provider class
class ExampleLLMProvider:
    """Example LLM provider that demonstrates integration of prompt engineering."""

    def __init__(self):
        self.logger = logging.getLogger("example_llm_provider")

    async def generate_content(
        self,
        state: AdventureState,
        lesson_question: Optional[LessonQuestion] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate content using the prompt engineering functions."""
        # Generate prompts using the integrated function
        system_prompt, user_prompt = generate_llm_prompts(
            state, lesson_question, previous_lessons
        )

        # Log the prompts for debugging
        self.logger.debug("\n=== DEBUG: System Prompt ===")
        self.logger.debug(system_prompt)
        self.logger.debug("\n=== DEBUG: User Prompt ===")
        self.logger.debug(user_prompt)

        # Here you would call your actual LLM service with the prompts
        # For example:
        # response = await self.llm_client.generate(
        #     system_prompt=system_prompt,
        #     user_prompt=user_prompt,
        # )
        # return response.content

        # For demonstration purposes, just return a placeholder
        return f"Generated content for chapter {state.current_chapter_number}"


# Example of how to update the existing providers.py file
"""
# In app/services/llm/providers.py

from app.services.llm.prompt_engineering import build_prompt

class GeminiService(LLMService):
    # ... existing code ...
    
    async def generate_chapter_stream(
        self,
        state: AdventureState,
        lesson_question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        # Generate prompts using the build_prompt function
        system_prompt, user_prompt = build_prompt(
            state=state,
            lesson_question=lesson_question,
            previous_lessons=previous_lessons,
        )
        
        # ... rest of the existing code ...
"""
