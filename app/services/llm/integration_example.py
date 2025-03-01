"""
Integration example for streamlined prompts.

This module demonstrates how to integrate the streamlined prompts into the
existing LLM service in the Learning Odyssey application.
"""

from typing import Optional, Dict, Any, List, Tuple
import logging
from app.models.story import AdventureState, ChapterType
from app.services.llm.prompt_engineering import (
    build_system_prompt,
    build_user_prompt,
    LessonQuestion,
)
from app.services.llm.streamlined_prompt_engineering import build_streamlined_prompt


def generate_llm_prompts(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """Generate system and user prompts for LLM, using streamlined prompts for first chapter.

    This function demonstrates how to integrate the streamlined prompts into the
    existing LLM service. It uses the streamlined prompts for the first chapter
    and falls back to the original prompts for other chapters.

    Args:
        state: The current adventure state
        lesson_question: Optional question data for lesson chapters
        previous_lessons: Optional history of previous lesson responses

    Returns:
        A tuple containing (system_prompt, user_prompt)
    """
    logger = logging.getLogger("llm_service")

    # For the first chapter, use the streamlined prompts
    if (
        state.current_chapter_number == 1
        and state.planned_chapter_types[0] == ChapterType.STORY
    ):
        logger.info("Using streamlined prompts for first chapter")
        return build_streamlined_prompt(state, lesson_question, previous_lessons)

    # For other chapters, use the original prompts
    logger.info(f"Using original prompts for chapter {state.current_chapter_number}")
    system_prompt = build_system_prompt(state)
    user_prompt = build_user_prompt(state, lesson_question, previous_lessons)

    return system_prompt, user_prompt


# Example usage in an LLM provider class
class ExampleLLMProvider:
    """Example LLM provider that demonstrates integration of streamlined prompts."""

    def __init__(self):
        self.logger = logging.getLogger("example_llm_provider")

    async def generate_content(
        self,
        state: AdventureState,
        lesson_question: Optional[LessonQuestion] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate content using the appropriate prompts based on chapter number."""
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

from app.services.llm.streamlined_prompt_engineering import build_streamlined_prompt

class GeminiService(LLMService):
    # ... existing code ...
    
    async def generate_content(
        self,
        state: AdventureState,
        lesson_question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # For the first chapter, use the streamlined prompts
        if state.current_chapter_number == 1 and state.planned_chapter_types[0] == ChapterType.STORY:
            system_prompt, user_prompt = build_streamlined_prompt(state, lesson_question, previous_lessons)
        else:
            # For other chapters, use the original prompts
            system_prompt = build_system_prompt(state)
            user_prompt = build_user_prompt(state, lesson_question, previous_lessons)
        
        # ... rest of the existing code ...
"""
