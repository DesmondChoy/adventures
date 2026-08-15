"""LLM provider routing by application use case."""

from dataclasses import dataclass
from typing import ClassVar, Literal

from .base import BaseLLMService
from .providers import GeminiService, ModelConfig, OpenAIService


@dataclass(frozen=True)
class UseCaseConfig:
    provider: Literal["openai", "gemini"]
    model: str


class LLMServiceFactory:
    """Create the configured provider for a known LLM use case."""

    USE_CASE_CONFIG_MAP: ClassVar[dict[str, UseCaseConfig]] = {
        # Narrative and related scene analysis use GPT-5.6 Luna.
        "story_generation": UseCaseConfig(
            provider="openai",
            model=ModelConfig.STORY_GENERATION_MODEL,
        ),
        "image_scene_generation": UseCaseConfig(
            provider="openai",
            model=ModelConfig.IMAGE_SCENE_MODEL,
        ),
        # Lightweight support work remains on Gemini Flash Lite.
        "character_visual_processing": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.CHARACTER_VISUAL_MODEL,
        ),
        "summary_generation": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.SUMMARY_MODEL,
        ),
        "paragraph_formatting": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.PARAGRAPH_FORMAT_MODEL,
        ),
        "chapter_summaries": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.CHAPTER_SUMMARY_MODEL,
        ),
        "fallback_summaries": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.CHAPTER_SUMMARY_MODEL,
        ),
        "image_prompt_synthesis": UseCaseConfig(
            provider="gemini",
            model=ModelConfig.IMAGE_PROMPT_MODEL,
        ),
    }

    @classmethod
    def _config_for(cls, use_case: str) -> UseCaseConfig:
        try:
            return cls.USE_CASE_CONFIG_MAP[use_case]
        except KeyError as exc:
            raise ValueError(f"Unknown LLM use case: {use_case}") from exc

    @classmethod
    def create_for_use_case(cls, use_case: str) -> BaseLLMService:
        config = cls._config_for(use_case)
        if config.provider == "openai":
            return OpenAIService(model=config.model)
        return GeminiService(model=config.model)

    @classmethod
    def create_flash_lite(cls) -> BaseLLMService:
        """Create a Gemini Flash Lite service for explicit support-task use."""
        return GeminiService(model=ModelConfig.GEMINI_FLASH_LITE_MODEL)

    @classmethod
    def get_model_for_use_case(cls, use_case: str) -> str:
        return cls._config_for(use_case).model

    @classmethod
    def is_flash_lite_use_case(cls, use_case: str) -> bool:
        return cls._config_for(use_case).model == ModelConfig.GEMINI_FLASH_LITE_MODEL
