from app.services.llm.base import BaseLLMService
from app.services.llm.providers import OpenAIService, GeminiService
from app.services.llm.factory import (
    LLMServiceFactory,
    LLMServiceFlash,
    LLMServiceFlashLite
)

# Default service for backward compatibility
LLMService = GeminiService

# Factory for service selection
ServiceFactory = LLMServiceFactory
