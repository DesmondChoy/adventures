import base64
from collections.abc import AsyncIterator
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PIL import Image

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


def test_generate_image_uses_nano_banana_2_at_1k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(source, format="PNG")
    inline_data = SimpleNamespace(data=source.getvalue())
    part = SimpleNamespace(inline_data=inline_data)
    content = SimpleNamespace(parts=[part])
    response = SimpleNamespace(candidates=[SimpleNamespace(content=content)])
    generate_content = MagicMock(return_value=response)

    client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(
        "app.services.image_generation_service.genai.Client",
        MagicMock(return_value=client),
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    service = ImageGenerationService()

    result = service._generate_image("A clockwork city", retries=0)

    assert result is not None
    with Image.open(BytesIO(base64.b64decode(result))) as generated:
        assert generated.format == "JPEG"

    call = generate_content.call_args
    assert call.kwargs["model"] == "gemini-3.1-flash-image"
    assert call.kwargs["contents"] == "A clockwork city"
    assert call.kwargs["config"].response_modalities == ["IMAGE"]
    assert call.kwargs["config"].image_config.aspect_ratio == "1:1"
    assert call.kwargs["config"].image_config.image_size == "1K"


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
