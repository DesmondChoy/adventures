"""Real HTTP + SQLite contract tests for the Memory Lane summary API."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user_id_optional
from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    StoryChoice,
)
from app.routers import summary_router
from app.services.summary import SummaryService
from tests.helpers.sqlite_state_storage import SQLiteAdventureStorage


def _build_completed_state() -> AdventureState:
    choices = [
        StoryChoice(text=f"Choice {i}", next_chapter=f"path_{i}") for i in range(1, 4)
    ]
    return AdventureState(
        current_chapter_id="chapter-2",
        story_length=2,
        planned_chapter_types=[ChapterType.STORY, ChapterType.CONCLUSION],
        selected_narrative_elements={"settings": "Clockwork Sky City"},
        selected_sensory_details={"visuals": "Brass", "sounds": "Chimes", "smells": "Rain"},
        selected_theme="Curiosity",
        selected_moral_teaching="Keep asking questions",
        selected_plot_twist="The sky map unfolds",
        chapters=[
            ChapterData(
                chapter_number=1,
                content="The journey begins above the clouds.",
                chapter_type=ChapterType.STORY,
                chapter_content=ChapterContent(
                    content="The journey begins above the clouds.",
                    choices=choices,
                ),
            ),
            ChapterData(
                chapter_number=2,
                content="The adventure reaches its conclusion.",
                chapter_type=ChapterType.CONCLUSION,
                chapter_content=ChapterContent(
                    content="The adventure reaches its conclusion.",
                    choices=[],
                ),
            ),
        ],
        chapter_summaries=["The explorer begins.", "The explorer finishes."],
        summary_chapter_titles=["Cloud Harbor", "Home Again"],
        metadata={"story_category": "clockwork_sky_city", "lesson_topic": "Astronomy"},
    )


def _make_summary_app(
    storage: SQLiteAdventureStorage,
    current_user_id: UUID | None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(summary_router.router, prefix="/adventure")
    app.dependency_overrides[summary_router.get_summary_service] = lambda: SummaryService(
        storage  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_current_user_id_optional] = lambda: current_user_id
    return app


def _stub_telemetry() -> MagicMock:
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.gte.return_value = query
    query.execute.return_value = MagicMock(data=[{"id": "recent-event"}])
    telemetry = MagicMock()
    telemetry.supabase.table.return_value = query
    telemetry.log_event = AsyncMock()
    return telemetry


@pytest.fixture
def sqlite_storage() -> Iterator[SQLiteAdventureStorage]:
    storage = SQLiteAdventureStorage()
    try:
        yield storage
    finally:
        storage.close()


@pytest.mark.asyncio
async def test_summary_http_endpoint_normalizes_duplicate_state_id_against_real_db(
    sqlite_storage: SQLiteAdventureStorage,
) -> None:
    state_id = "36d9319b-02c7-47c9-b0a4-99657dd99016"
    state = _build_completed_state()
    await sqlite_storage.store_state(
        state.model_dump(mode="json"),
        new_adventure_id=state_id,
        explicit_is_complete=True,
    )

    app = _make_summary_app(sqlite_storage, current_user_id=None)
    with patch(
        "app.routers.summary_router.get_telemetry_service",
        return_value=_stub_telemetry(),
    ), TestClient(app) as client:
        response = client.get(
            f"/adventure/api/adventure-summary?state_id={state_id},{state_id}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert [c["chapterType"] for c in payload["chapterSummaries"]] == [
        "story",
        "conclusion",
    ]
    assert payload["statistics"]["chaptersCompleted"] == 2


@pytest.mark.asyncio
async def test_summary_http_endpoint_enforces_owner_isolation_against_real_db(
    sqlite_storage: SQLiteAdventureStorage,
) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()
    state_id = str(uuid4())
    await sqlite_storage.store_state(
        _build_completed_state().model_dump(mode="json"),
        new_adventure_id=state_id,
        user_id=owner_id,
        explicit_is_complete=True,
    )

    with patch(
        "app.routers.summary_router.get_telemetry_service",
        return_value=_stub_telemetry(),
    ):
        with TestClient(_make_summary_app(sqlite_storage, other_user_id)) as other_client:
            denied = other_client.get(f"/adventure/api/adventure-summary?state_id={state_id}")
        with TestClient(_make_summary_app(sqlite_storage, None)) as guest_client:
            unauth = guest_client.get(f"/adventure/api/adventure-summary?state_id={state_id}")
        with TestClient(_make_summary_app(sqlite_storage, owner_id)) as owner_client:
            allowed = owner_client.get(f"/adventure/api/adventure-summary?state_id={state_id}")

    assert denied.status_code == 403
    assert unauth.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["statistics"]["chaptersCompleted"] == 2
