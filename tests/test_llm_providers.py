import asyncio
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
    caplog: pytest.LogCaptureFixture,
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
        metadata={"adventure_id": "adventure-123"},
    )

    with caplog.at_level("INFO", logger="story_app"):
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
    request_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI structured chapter request"
    )
    response_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI structured chapter validated"
    )
    assert request_record.llm_call_id == response_record.llm_call_id
    assert request_record.adventure_id == "adventure-123"
    assert response_record.adventure_id == "adventure-123"
    assert request_record.llm_prompt == {"system": "system", "user": "user"}
    assert response_record.llm_response == {
        "content": "Mira reached the glowing bridge.",
        "choices": ["Cross it", "Follow the river", "Ask the wind"],
    }


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


@pytest.mark.asyncio
async def test_openai_failed_request_retains_call_and_adventure_correlation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = OpenAIService.__new__(OpenAIService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        responses=SimpleNamespace(
            create=AsyncMock(side_effect=RuntimeError("temporary failure"))
        )
    )

    with caplog.at_level("INFO", logger="story_app"):
        with pytest.raises(RuntimeError, match="temporary failure"):
            await service._generate_text(
                "system",
                "user",
                use_case="test",
                context={
                    "adventure_id": "adventure-123",
                    "chapter_number": 4,
                    "chapter_type": "story",
                },
            )

    request_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI text request"
    )
    failure_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI text request failed"
    )
    assert request_record.llm_call_id == failure_record.llm_call_id
    assert failure_record.adventure_id == "adventure-123"
    assert failure_record.chapter_number == 4


@pytest.mark.asyncio
async def test_openai_cancelled_request_has_correlated_terminal_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = OpenAIService.__new__(OpenAIService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        responses=SimpleNamespace(
            create=AsyncMock(side_effect=asyncio.CancelledError())
        )
    )

    with caplog.at_level("INFO", logger="story_app"):
        with pytest.raises(asyncio.CancelledError):
            await service._generate_text(
                "system",
                "user",
                use_case="test",
                context={"adventure_id": "adventure-123"},
            )

    request_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI text request"
    )
    cancelled_record = next(
        record
        for record in caplog.records
        if record.message == "OpenAI text request cancelled"
    )
    assert request_record.llm_call_id == cancelled_record.llm_call_id
    assert cancelled_record.adventure_id == "adventure-123"


@pytest.mark.asyncio
async def test_gemini_direct_request_and_response_share_correlation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = GeminiService.__new__(GeminiService)
    service.model = "test-model"
    service.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=MagicMock(
                return_value=SimpleNamespace(text='{"Mira": "Red coat"}')
            )
        )
    )

    with caplog.at_level("INFO", logger="story_app"):
        response = await service.generate_character_visuals_json(
            "prompt",
            context={
                "adventure_id": "adventure-123",
                "chapter_number": 2,
                "chapter_type": "reflect",
            },
        )

    assert response == '{"Mira": "Red coat"}'
    request_record = next(
        record
        for record in caplog.records
        if record.message == "Gemini direct text request"
    )
    response_record = next(
        record
        for record in caplog.records
        if record.message == "Gemini direct text response"
    )
    assert request_record.llm_call_id == response_record.llm_call_id
    assert response_record.adventure_id == "adventure-123"
    assert response_record.chapter_number == 2
