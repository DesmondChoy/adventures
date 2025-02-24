from typing import Any, Dict, Optional, List, AsyncGenerator
from abc import ABC, abstractmethod
from app.models.story import AdventureState
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger("story_app")


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    @asynccontextmanager
    async def log_llm_interaction(self, prompt: str, context: Dict[str, Any] = None):
        """Context manager to log LLM interactions with proper request context."""
        if context is None:
            context = {}

        # Log the prompt
        logger.info(
            "Sending prompt to LLM",
            extra={
                "llm_prompt": prompt,
                "session_id": context.get("session_id", "no_session"),
                "request_id": context.get("request_id", "no_request_id"),
            },
        )

        try:
            yield
        except Exception as e:
            logger.error(
                f"Error in LLM interaction: {str(e)}",
                extra={
                    "llm_prompt": prompt,
                    "error": str(e),
                    "session_id": context.get("session_id", "no_session"),
                    "request_id": context.get("request_id", "no_request_id"),
                },
            )
            raise

    async def log_llm_response(self, response: str, context: Dict[str, Any] = None):
        """Helper method to log LLM responses."""
        if context is None:
            context = {}

        logger.info(
            "Received response from LLM",
            extra={
                "llm_response": response,
                "session_id": context.get("session_id", "no_session"),
                "request_id": context.get("request_id", "no_request_id"),
            },
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
