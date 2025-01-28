from app.services.llm.base import BaseLLMService
from app.services.llm.providers import OpenAIService

# Default service for backward compatibility
LLMService = OpenAIService
