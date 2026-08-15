from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.models.story import AdventureState
from app.services.llm.chapter_output import GeneratedChapter


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    async def generate_structured_chapter(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedChapter:
        """Generate a validated chapter using the provider's structured output API."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support structured chapter generation"
        )

    @abstractmethod
    async def generate_chapter_stream(
        self,
        story_config: Dict[str, Any],
        state: AdventureState,
        question: Optional[Dict[str, Any]] = None,
        previous_lessons: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the chapter content (story or lesson) as a stream of chunks."""
        pass

    @abstractmethod
    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate content with custom system and user prompts as a stream of chunks."""
        pass
        
    @abstractmethod
    async def generate_character_visuals_json(
        self,
        custom_prompt: str,
        use_case: str = "character_visuals",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate character visuals JSON with direct response (no streaming).
        
        This method is specifically for character visual extraction where we need
        the complete response before processing. It avoids streaming to ensure
        we get a complete JSON response.
        
        Args:
            custom_prompt: The prompt to send to the LLM
            use_case: Audit label for the direct-text request
            context: Correlation metadata for the request
            
        Returns:
            str: Complete response text from the LLM
        """
        pass
