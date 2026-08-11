from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.image_generation_service import ImageGenerationService
from app.services.llm.factory import LLMServiceFactory


class _FakeGeminiService:
    model = "test-model"

    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "A detailed synthesized image prompt."


@pytest.mark.asyncio
async def test_image_prompt_fallback_consumes_async_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_llm = _FakeGeminiService()

    def create_for_use_case(
        _cls: type[LLMServiceFactory], _use_case: str
    ) -> _FakeGeminiService:
        return fake_llm

    monkeypatch.setattr(
        LLMServiceFactory,
        "create_for_use_case",
        classmethod(create_for_use_case),
    )

    service = ImageGenerationService.__new__(ImageGenerationService)
    generate_content = MagicMock(side_effect=RuntimeError("temporary failure"))
    service.client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )

    result = await service.synthesize_image_prompt(
        image_scene_description="A bridge above glowing water",
        protagonist_description="A child in a red coat",
        agency_details={},
        story_visual_sensory_detail="blue moonlight",
    )

    assert result == "A detailed synthesized image prompt."
    generate_content.assert_called_once()
