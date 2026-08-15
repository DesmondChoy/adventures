"""Tests for the read-only Supabase audit used after live browser E2E."""

from copy import deepcopy
from uuid import uuid4

from tools.audit_e2e_supabase import audit_records


def _complete_records() -> tuple[str, dict, list[dict]]:
    state_id = str(uuid4())
    owner_id = str(uuid4())
    client_uuid = str(uuid4())
    chapter_types = [
        "story",
        "lesson",
        "story",
        "lesson",
        "story",
        "lesson",
        "reflect",
        "story",
        "story",
        "conclusion",
        "summary",
    ]
    chapters = []
    for chapter_number, chapter_type in enumerate(chapter_types, start=1):
        chapter = {
            "chapter_number": chapter_number,
            "chapter_type": chapter_type,
            "content": f"Persisted content for chapter {chapter_number}.",
            "question": None,
            "response": None,
        }
        if chapter_type == "lesson":
            chapter["question"] = {"question": "Fixture question"}
            chapter["response"] = {
                "chosen_answer": "Fixture answer",
                "is_correct": True,
            }
        chapters.append(chapter)

    adventure = {
        "id": state_id,
        "user_id": owner_id,
        "client_uuid": client_uuid,
        "story_category": "clockwork_sky_city",
        "lesson_topic": "Astronomy",
        "is_complete": True,
        "completed_chapter_count": 11,
        "environment": "test",
        "state_data": {
            "story_length": 10,
            "planned_chapter_types": chapter_types[:10],
            "chapters": chapters,
            "chapter_summaries": [
                f"Meaningful summary {number}" for number in range(1, 11)
            ],
            "summary_chapter_titles": [
                f"The Clockwork Discovery {number}" for number in range(1, 11)
            ],
            "metadata": {"adventure_id": state_id},
        },
    }

    def event(
        event_name: str,
        *,
        chapter_number: int | None = None,
        metadata: dict | None = None,
    ) -> dict:
        chapter_type = (
            chapter_types[chapter_number - 1] if chapter_number is not None else None
        )
        return {
            "event_name": event_name,
            "adventure_id": state_id,
            "user_id": owner_id,
            "timestamp": "2026-08-15T12:00:00+00:00",
            "metadata": metadata or {},
            "environment": "test",
            "chapter_type": chapter_type,
            "chapter_number": chapter_number,
            "event_duration_seconds": None,
        }

    events = [
        event(
            "adventure_started",
            metadata={
                "story_category": adventure["story_category"],
                "lesson_topic": adventure["lesson_topic"],
                "client_uuid": client_uuid,
            },
        ),
        *(event("chapter_viewed", chapter_number=number) for number in range(1, 11)),
        *(event("choice_made", chapter_number=number) for number in range(1, 11)),
        event("summary_viewed"),
    ]
    return state_id, adventure, events


def test_complete_supabase_records_pass_audit() -> None:
    state_id, adventure, events = _complete_records()

    result = audit_records(adventure, events, state_id=state_id)

    assert result.passed
    assert result.errors == []
    assert result.stored_chapter_count == 11
    assert result.summary_count == 10
    assert result.lesson_answer_count == 3


def test_missing_conclusion_view_fails_audit() -> None:
    state_id, adventure, events = _complete_records()
    events = [
        event
        for event in events
        if not (
            event["event_name"] == "chapter_viewed" and event["chapter_number"] == 10
        )
    ]

    result = audit_records(adventure, events, state_id=state_id)

    assert not result.passed
    assert any("chapter_viewed" in error for error in result.errors)


def test_duplicate_choice_and_wrong_owner_fail_audit() -> None:
    state_id, adventure, events = _complete_records()
    events.append(
        deepcopy(
            next(event for event in events if event["event_name"] == "choice_made")
        )
    )
    events[1]["user_id"] = str(uuid4())

    result = audit_records(adventure, events, state_id=state_id)

    assert not result.passed
    assert any("owner" in error for error in result.errors)
    assert any("choice_made" in error for error in result.errors)
