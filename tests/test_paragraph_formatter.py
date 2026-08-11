from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.services.llm.paragraph_formatter import reformat_text_with_paragraphs


class _FakeLLMService:
    def __init__(self) -> None:
        self.context: dict[str, Any] | None = None

    async def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        self.context = context
        yield "First paragraph.\n\nSecond paragraph."


@pytest.mark.asyncio
async def test_reformat_text_consumes_async_generator_directly() -> None:
    original = (
        "Sentence one. Sentence two. Sentence three. Sentence four. "
        "Sentence five. Sentence six. Sentence seven. Sentence eight. "
        "Sentence nine. Sentence ten. Sentence eleven. Sentence twelve. "
        "Sentence thirteen. Sentence fourteen. Sentence fifteen. Sentence sixteen."
    )

    llm_service = _FakeLLMService()
    result = await reformat_text_with_paragraphs(
        original,
        max_attempts=1,
        llm_service=llm_service,
    )

    assert result == "First paragraph.\n\nSecond paragraph."
    assert llm_service.context == {"skip_paragraph_formatting": True}
