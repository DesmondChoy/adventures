from unittest.mock import MagicMock

import pytest

import app.services.llm.factory as factory_module
from app.services.llm.factory import LLMServiceFactory
from app.services.llm.providers import ModelConfig


@pytest.mark.parametrize("use_case", ["story_generation", "image_scene_generation"])
def test_complex_text_generation_routes_to_openai_luna(
    monkeypatch: pytest.MonkeyPatch,
    use_case: str,
) -> None:
    openai_service = MagicMock()
    monkeypatch.setattr(factory_module, "OpenAIService", openai_service)

    LLMServiceFactory.create_for_use_case(use_case)

    openai_service.assert_called_once_with(model="gpt-5.6-luna")


@pytest.mark.parametrize(
    "use_case",
    [
        "summary_generation",
        "chapter_summaries",
        "fallback_summaries",
        "paragraph_formatting",
        "character_visual_processing",
        "image_prompt_synthesis",
    ],
)
def test_support_tasks_remain_on_gemini_flash_lite(
    monkeypatch: pytest.MonkeyPatch,
    use_case: str,
) -> None:
    gemini_service = MagicMock()
    monkeypatch.setattr(factory_module, "GeminiService", gemini_service)

    LLMServiceFactory.create_for_use_case(use_case)

    gemini_service.assert_called_once_with(
        model=ModelConfig.GEMINI_FLASH_LITE_MODEL
    )


def test_unknown_use_case_has_no_provider_fallback() -> None:
    with pytest.raises(ValueError, match="Unknown LLM use case"):
        LLMServiceFactory.create_for_use_case("unknown")
