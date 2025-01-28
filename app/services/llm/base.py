from typing import Any, Dict, Optional, List, AsyncGenerator
from abc import ABC, abstractmethod
from app.models.story import StoryState


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    @abstractmethod
    async def generate_story_stream(
        self,
        story_config: Dict[str, Any],
        state: StoryState,
        question: Optional[Dict[str, Any]] = None,
        previous_questions: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate the story segment as a stream of chunks."""
        pass
