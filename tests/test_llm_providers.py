from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.llm.providers as providers
from app.models.story import AdventureState
from app.services.llm.providers import GeminiService, OpenAIService

ServiceFactory = Callable[[list[str]], OpenAIService | GeminiService]


async def _openai_chunks(parts: list[str]) -> AsyncIterator[SimpleNamespace]:
    for part in parts:
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=part))]
        )


async def _collect_text(stream: AsyncIterator[str]) -> str:
    return "".join([chunk async for chunk in stream])


def _openai_service(parts: list[str]) -> OpenAIService:
    service = OpenAIService.__new__(OpenAIService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_openai_chunks(parts))
            )
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
