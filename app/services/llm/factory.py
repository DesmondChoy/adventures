"""
LLM Service Factory for routing between Flash and Flash Lite models.

Provides centralized model selection based on use case complexity:
- Flash: Complex reasoning (story generation, image scenes)
- Flash Lite: Simple processing (summaries, formatting, JSON extraction)
"""

from typing import Optional
from .base import BaseLLMService
from .providers import GeminiService, ModelConfig


class LLMServiceFactory:
    """Factory for creating appropriate LLM service instances based on use case complexity."""
    
    # Use case to model mapping
    USE_CASE_MODEL_MAP = {
        # Complex reasoning - keep Flash for quality
        "story_generation": ModelConfig.GEMINI_MODEL,
        "image_scene_generation": ModelConfig.GEMINI_MODEL,
        
        # Simple processing - use Flash Lite for cost efficiency
        "character_visual_processing": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        "summary_generation": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        "paragraph_formatting": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        "chapter_summaries": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        "fallback_summaries": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        "image_prompt_synthesis": ModelConfig.GEMINI_FLASH_LITE_MODEL,
        
        # Default fallback
        "default": ModelConfig.GEMINI_MODEL,
    }
    
    @classmethod
    def create_for_use_case(cls, use_case: str) -> BaseLLMService:
        """
        Create appropriate LLM service based on use case complexity.
        
        Args:
            use_case: The specific use case determining model complexity needs
            
        Returns:
            Configured LLM service instance with appropriate model
        """
        model = cls.USE_CASE_MODEL_MAP.get(use_case, cls.USE_CASE_MODEL_MAP["default"])
        return GeminiService(model=model)
    
    @classmethod
    def create_flash(cls) -> BaseLLMService:
        """Create Flash service for complex reasoning tasks."""
        return GeminiService(model=ModelConfig.GEMINI_MODEL)
    
    @classmethod
    def create_flash_lite(cls) -> BaseLLMService:
        """Create Flash Lite service for simple processing tasks."""
        return GeminiService(model=ModelConfig.GEMINI_FLASH_LITE_MODEL)
    
    @classmethod
    def get_model_for_use_case(cls, use_case: str) -> str:
        """Get the model name for a specific use case."""
        return cls.USE_CASE_MODEL_MAP.get(use_case, cls.USE_CASE_MODEL_MAP["default"])
    
    @classmethod
    def is_flash_lite_use_case(cls, use_case: str) -> bool:
        """Check if a use case should use Flash Lite model."""
        return cls.get_model_for_use_case(use_case) == ModelConfig.GEMINI_FLASH_LITE_MODEL


# Convenience instances for direct import
LLMServiceFlash = lambda: LLMServiceFactory.create_flash()
LLMServiceFlashLite = lambda: LLMServiceFactory.create_flash_lite()
