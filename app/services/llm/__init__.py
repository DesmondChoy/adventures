from app.services.llm.base import BaseLLMService
from app.services.llm.providers import OpenAIService, GeminiService

# Default service for backward compatibility
LLMService = GeminiService
