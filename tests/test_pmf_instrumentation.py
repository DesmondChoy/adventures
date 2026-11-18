"""Attribution, end-of-story feedback, and chapter-1 telemetry plumbing."""

from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rate_limit import limiter
from app.routers import client_telemetry_router, feedback_router
from app.routers.websocket_router import ATTRIBUTION_MAX_LENGTH, build_attribution
from app.services.feedback_service import FeedbackService

ADVENTURE_ID = "11111111-1111-4111-8111-111111111111"


def test_build_attribution_keeps_trimmed_non_empty_values() -> None:
    attribution = build_attribution(
        utm_source="  whatsapp ",
        utm_medium="",
        utm_campaign=None,
        utm_content="x" * (ATTRIBUTION_MAX_LENGTH + 50),
        referrer="www.facebook.com",
    )

    assert attribution == {
        "utm_source": "whatsapp",
        "utm_content": "x" * ATTRIBUTION_MAX_LENGTH,
        "referrer": "www.facebook.com",
    }


def test_build_attribution_is_empty_without_tags() -> None:
    assert build_attribution(utm_source=None, referrer="  ") == {}


class FakeTelemetryService:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    async def log_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


class FakeFeedbackService:
    def __init__(self) -> None:
        self.checks: List[Dict[str, Any]] = []

    async def has_user_given_feedback(self, **kwargs: Any) -> bool:
        self.checks.append(kwargs)
        return kwargs.get("chapter_number") is None


@pytest.fixture
def services():
    telemetry = FakeTelemetryService()
    feedback = FakeFeedbackService()
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(client_telemetry_router.router)
    app.include_router(feedback_router.router)
    app.dependency_overrides[client_telemetry_router.get_telemetry_service_dep] = (
        lambda: telemetry
    )
    app.dependency_overrides[feedback_router.get_feedback_service_dep] = (
        lambda: feedback
    )
    with TestClient(app) as client:
        yield client, telemetry, feedback


def test_client_event_logs_allow_listed_chapter_one_event(services) -> None:
    client, telemetry, _ = services

    response = client.post(
        "/api/telemetry/client-event",
        json={
            "event_name": "chapter1_exit",
            "adventure_id": ADVENTURE_ID,
            "metadata": {
                "ms_since_start": 4200.7,
                "trigger": "pagehide",
                "last_milestone": "chapter1_text_shown",
                "client_uuid": "guest-123",
                "unexpected": "dropped",
            },
        },
    )

    assert response.status_code == 204
    assert telemetry.events == [
        {
            "event_name": "chapter1_exit",
            "adventure_id": UUID(ADVENTURE_ID),
            "user_id": None,
            "metadata": {
                "ms_since_start": 4200,
                "trigger": "pagehide",
                "last_milestone": "chapter1_text_shown",
                "client_uuid": "guest-123",
            },
            "chapter_number": 1,
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"event_name": "anything_else", "adventure_id": ADVENTURE_ID},
        {"event_name": "chapter1_choice_clicked", "adventure_id": "not-a-uuid"},
    ],
)
def test_client_event_rejects_unknown_events_and_bad_ids(services, payload) -> None:
    client, telemetry, _ = services

    response = client.post("/api/telemetry/client-event", json=payload)

    assert response.status_code == 400
    assert telemetry.events == []


def test_end_of_story_feedback_check_is_scoped_to_its_chapter(services) -> None:
    client, _, feedback = services

    mid = client.get("/api/feedback/check", params={"client_uuid": "guest-123"})
    end = client.get(
        "/api/feedback/check",
        params={"client_uuid": "guest-123", "chapter_number": 10},
    )

    # Fake: any earlier feedback exists, but none at chapter 10.
    assert mid.json() == {"has_given_feedback": True}
    assert end.json() == {"has_given_feedback": False}
    assert [check["chapter_number"] for check in feedback.checks] == [None, 10]


class FakeQuery:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self.rows = rows
        self.filters: List[tuple] = []

    def select(self, _columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self.filters.append((column, value))
        return self

    def limit(self, _n: int) -> "FakeQuery":
        return self

    def execute(self):
        rows = [
            row
            for row in self.rows
            if all(row.get(column) == value for column, value in self.filters)
        ]
        return type("Response", (), {"data": rows})()


class FakeSupabase:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, _name: str) -> FakeQuery:
        return FakeQuery(self.rows)


@pytest.mark.parametrize(
    ("chapter_number", "expected"), [(None, True), (5, True), (10, False)]
)
async def test_feedback_history_can_be_checked_per_prompt(
    chapter_number: Optional[int], expected: bool
) -> None:
    service = object.__new__(FeedbackService)
    service.supabase = FakeSupabase(
        [{"id": "f1", "client_uuid": "guest-123", "chapter_number": 5}]
    )

    assert (
        await service.has_user_given_feedback(
            client_uuid="guest-123", chapter_number=chapter_number
        )
        is expected
    )
