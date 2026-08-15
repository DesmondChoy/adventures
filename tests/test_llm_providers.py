from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.llm.providers as providers
from app.models.story import AdventureState, ChapterType
from app.services.llm.chapter_output import StoryChapterResponse
from app.services.llm.providers import GeminiService, ModelConfig, OpenAIService

ServiceFactory = Callable[[list[str]], OpenAIService | GeminiService]


async def _collect_text(stream: AsyncIterator[str]) -> str:
    return "".join([chunk async for chunk in stream])


def _openai_service(parts: list[str]) -> OpenAIService:
    service = OpenAIService.__new__(OpenAIService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        responses=SimpleNamespace(
            create=AsyncMock(
                return_value=SimpleNamespace(
                    id="response-id",
                    status="completed",
                    output_text="".join(parts),
                    output=[],
                    usage=None,
                )
            ),
        )
    )
    return service


def _gemini_service(parts: list[str]) -> GeminiService:
    service = GeminiService.__new__(GeminiService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content_stream=MagicMock(
                return_value=[SimpleNamespace(text=part) for part in parts]
            )
        )
    )
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize("service_factory", [_openai_service, _gemini_service])
async def test_generate_with_prompt_flushes_short_response(
    service_factory: ServiceFactory,
) -> None:
    service = service_factory(["A short ", "response."])

    result = await _collect_text(
        service.generate_with_prompt(system_prompt="system", user_prompt="user")
    )

    assert result == "A short response."


@pytest.mark.asyncio
@pytest.mark.parametrize("service_factory", [_openai_service, _gemini_service])
async def test_generate_chapter_stream_flushes_short_response(
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    def fake_build_prompt(**_kwargs: Any) -> tuple[str, str]:
        return "system", "user"

    monkeypatch.setattr(providers, "build_prompt", fake_build_prompt)
    service = service_factory(["Short chapter."])

    result = await _collect_text(
        service.generate_chapter_stream(
            story_config={},
            state=cast(AdventureState, object()),
        )
    )

    assert result == "Short chapter."


@pytest.mark.asyncio
@pytest.mark.parametrize("service_factory", [_openai_service, _gemini_service])
async def test_generate_with_prompt_can_skip_paragraph_repair(
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    async def fail_if_called(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("paragraph repair should be bypassed")

    monkeypatch.setattr(providers, "regenerate_with_paragraphs", fail_if_called)
    response = "A sentence without paragraph breaks. " * 20
    service = service_factory([response])

    result = await _collect_text(
        service.generate_with_prompt(
            system_prompt="system",
            user_prompt="user",
            context={"skip_paragraph_formatting": True},
        )
    )

    assert result == response


@pytest.mark.asyncio
async def test_openai_structured_chapter_uses_luna_low_reasoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(providers, "build_prompt", lambda **_kwargs: ("system", "user"))
    parsed = StoryChapterResponse(
        content="Mira reached the glowing bridge.",
        choices=["Cross it", "Follow the river", "Ask the wind"],
    )
    parse = AsyncMock(
        return_value=SimpleNamespace(
            id="response-id",
            status="completed",
            output_parsed=parsed,
            output=[],
            usage=None,
        )
    )
    service = OpenAIService.__new__(OpenAIService)
    service.model = ModelConfig.OPENAI_MODEL
    service.client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    state = SimpleNamespace(
        planned_chapter_types=[ChapterType.STORY],
        current_chapter_number=1,
        metadata={},
    )

    chapter = await service.generate_structured_chapter(
        story_config={},
        state=cast(AdventureState, state),
    )

    assert chapter.choices == ("Cross it", "Follow the river", "Ask the wind")
    request = parse.await_args.kwargs
    assert request["model"] == "gpt-5.6-luna"
    assert request["reasoning"] == {"effort": "low"}
    assert request["text_format"] is StoryChapterResponse
    assert request["store"] is False
    assert "temperature" not in request


def test_openai_service_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        OpenAIService()


def test_openai_incomplete_response_is_rejected() -> None:
    response = SimpleNamespace(
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
    )

    with pytest.raises(ValueError, match="max_output_tokens"):
        OpenAIService._ensure_completed(response)


@pytest.mark.asyncio
async def test_openai_empty_response_surfaces_refusal() -> None:
    response = SimpleNamespace(
        id="response-id",
        status="completed",
        output_text="",
        output=[
            SimpleNamespace(
                content=[
                    SimpleNamespace(type="refusal", refusal="Request refused")
                ]
            )
        ],
        usage=None,
    )
    service = OpenAIService.__new__(OpenAIService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        responses=SimpleNamespace(create=AsyncMock(return_value=response))
    )

    with pytest.raises(ValueError, match="Request refused"):
        await service._generate_text("system", "user", use_case="test")
