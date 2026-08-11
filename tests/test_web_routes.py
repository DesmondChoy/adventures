from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException, Request

from app.models.story import AdventureState
from app.routers import web

DEFAULT_STORY_LENGTH = int(AdventureState.model_fields["story_length"].default)


@pytest.mark.asyncio
@pytest.mark.parametrize("chapter", [0, DEFAULT_STORY_LENGTH + 1])
async def test_story_page_rejects_chapters_outside_state_limit(
    chapter: int,
) -> None:
    request = cast(
        Request,
        SimpleNamespace(session={"request_id": "test-request"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await web.story_page(request, chapter)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_story_page_accepts_state_story_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = cast(
        Request,
        SimpleNamespace(session={"request_id": "test-request"}),
    )
    response = object()

    async def select_adventure(_request: Request) -> object:
        return response

    monkeypatch.setattr(web, "select_adventure", select_adventure)
    result = await web.story_page(request, DEFAULT_STORY_LENGTH)

    assert result is response
