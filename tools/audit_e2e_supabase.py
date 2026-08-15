"""Read-only Supabase audit for a completed live browser E2E adventure."""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from dotenv import load_dotenv

from supabase import Client, create_client

PLACEHOLDER_TITLE = re.compile(
    r"(?:chapter\s+\d+|adventure chapter|chapter summary|"
    r"summary not available|a scene from the story)",
    re.IGNORECASE,
)
REQUIRED_EVENT_NAMES = (
    "adventure_started",
    "chapter_viewed",
    "choice_made",
    "summary_viewed",
)


@dataclass(frozen=True)
class AuditResult:
    errors: list[str]
    stored_chapter_count: int
    summary_count: int
    lesson_answer_count: int
    event_counts: dict[str, int]

    @property
    def passed(self) -> bool:
        return not self.errors


def audit_records(
    adventure: dict[str, Any] | None,
    events: list[dict[str, Any]],
    *,
    state_id: str,
    expected_story_length: int = 10,
    expected_lesson_count: int = 3,
) -> AuditResult:
    """Validate persisted state and telemetry for one completed adventure."""
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    if not adventure:
        return AuditResult(
            errors=["Adventure row was not found."],
            stored_chapter_count=0,
            summary_count=0,
            lesson_answer_count=0,
            event_counts={},
        )

    state = adventure.get("state_data")
    require(isinstance(state, dict), "Adventure state_data is not an object.")
    if not isinstance(state, dict):
        state = {}

    chapters = state.get("chapters")
    require(isinstance(chapters, list), "Adventure chapters are not a list.")
    if not isinstance(chapters, list):
        chapters = []

    story_length = state.get("story_length")
    require(
        story_length == expected_story_length,
        f"story_length must be {expected_story_length}; found {story_length!r}.",
    )
    require(adventure.get("is_complete") is True, "Adventure is not complete.")
    require(bool(adventure.get("user_id")), "Adventure has no authenticated owner.")
    require(bool(adventure.get("client_uuid")), "Adventure has no client UUID.")
    require(bool(adventure.get("story_category")), "Story category was not stored.")
    require(bool(adventure.get("lesson_topic")), "Lesson topic was not stored.")

    expected_stored_count = expected_story_length + 1
    chapter_numbers = [chapter.get("chapter_number") for chapter in chapters]
    chapter_types = [
        str(chapter.get("chapter_type", "")).lower() for chapter in chapters
    ]
    require(
        len(chapters) == expected_stored_count,
        "Persisted state must contain 10 journey chapters plus the summary chapter; "
        f"found {len(chapters)} entries.",
    )
    require(
        adventure.get("completed_chapter_count") == len(chapters),
        "completed_chapter_count does not match the persisted chapter list.",
    )
    require(
        chapter_numbers == list(range(1, expected_stored_count + 1)),
        "Persisted chapter numbers are not the contiguous sequence 1-11.",
    )
    require(
        len(state.get("planned_chapter_types") or []) == expected_story_length,
        "planned_chapter_types does not contain the 10-chapter journey plan.",
    )
    if len(chapter_types) >= expected_stored_count:
        require(
            chapter_types[expected_story_length - 1] == "conclusion",
            "Chapter 10 is not stored as the conclusion.",
        )
        require(
            chapter_types[expected_story_length] == "summary",
            "The final persisted entry is not the summary chapter.",
        )
    require(
        all(bool(str(chapter.get("content", "")).strip()) for chapter in chapters),
        "At least one persisted chapter has empty content.",
    )

    metadata = state.get("metadata") or {}
    require(isinstance(metadata, dict), "Adventure metadata is not an object.")
    if isinstance(metadata, dict):
        require(
            str(metadata.get("adventure_id")) == state_id,
            "state_data.metadata.adventure_id does not match the audited row.",
        )

    summaries = state.get("chapter_summaries") or []
    titles = state.get("summary_chapter_titles") or []
    require(
        isinstance(summaries, list) and len(summaries) == expected_story_length,
        "Exactly 10 chapter summaries were not persisted.",
    )
    if isinstance(summaries, list):
        require(
            all(bool(str(summary).strip()) for summary in summaries),
            "At least one persisted chapter summary is empty.",
        )
    require(
        isinstance(titles, list) and len(titles) == expected_story_length,
        "Exactly 10 summary titles were not persisted.",
    )
    if isinstance(titles, list):
        normalized_titles = [str(title).strip() for title in titles]
        require(
            all(
                title and not PLACEHOLDER_TITLE.fullmatch(title)
                for title in normalized_titles
            ),
            "At least one persisted summary title is empty or generic.",
        )
        require(
            len(set(normalized_titles)) == expected_story_length,
            "Persisted summary titles are not unique.",
        )

    lesson_chapters = [
        chapter
        for chapter in chapters[:expected_story_length]
        if str(chapter.get("chapter_type", "")).lower() == "lesson"
    ]
    require(
        len(lesson_chapters) == expected_lesson_count,
        f"Expected {expected_lesson_count} lesson chapters; found {len(lesson_chapters)}.",
    )
    answered_lessons = [
        chapter
        for chapter in lesson_chapters
        if isinstance(chapter.get("question"), dict)
        and isinstance(chapter.get("response"), dict)
        and bool(str(chapter["response"].get("chosen_answer", "")).strip())
        and isinstance(chapter["response"].get("is_correct"), bool)
    ]
    require(
        len(answered_lessons) == expected_lesson_count,
        "All three persisted lesson chapters do not contain a question and answer.",
    )

    counts = Counter(str(event.get("event_name")) for event in events)
    event_counts = {name: counts.get(name, 0) for name in REQUIRED_EVENT_NAMES}
    require(
        event_counts["adventure_started"] == 1, "adventure_started must occur once."
    )
    require(event_counts["summary_viewed"] >= 1, "summary_viewed was not logged.")

    owner_id = adventure.get("user_id")
    environment = adventure.get("environment")
    require(
        bool(environment) and environment != "unknown",
        "Adventure environment is missing or unknown.",
    )
    require(
        all(event.get("user_id") == owner_id for event in events),
        "At least one telemetry event is not linked to the adventure owner.",
    )
    require(
        all(event.get("environment") == environment for event in events),
        "Telemetry environment does not consistently match the adventure row.",
    )
    require(
        all(bool(event.get("timestamp")) for event in events),
        "At least one telemetry event has no timestamp.",
    )

    expected_journey_numbers = set(range(1, expected_story_length + 1))
    viewed_numbers = {
        event.get("chapter_number")
        for event in events
        if event.get("event_name") == "chapter_viewed"
    }
    require(
        viewed_numbers == expected_journey_numbers,
        "chapter_viewed does not cover every journey chapter from 1 through 10.",
    )

    choice_numbers = [
        event.get("chapter_number")
        for event in events
        if event.get("event_name") == "choice_made"
    ]
    require(
        Counter(choice_numbers) == Counter(range(1, expected_story_length + 1)),
        "choice_made must occur exactly once for every chapter from 1 through 10.",
    )

    persisted_types = {
        chapter.get("chapter_number"): str(chapter.get("chapter_type", "")).lower()
        for chapter in chapters[:expected_story_length]
    }
    for event in events:
        if event.get("event_name") not in {"chapter_viewed", "choice_made"}:
            continue
        chapter_number = event.get("chapter_number")
        expected_type = persisted_types.get(chapter_number)
        require(
            expected_type is not None
            and str(event.get("chapter_type", "")).lower() == expected_type,
            f"Telemetry chapter type does not match persisted Chapter {chapter_number}.",
        )

    started_events = [
        event for event in events if event.get("event_name") == "adventure_started"
    ]
    if len(started_events) == 1:
        started_metadata = started_events[0].get("metadata") or {}
        require(
            isinstance(started_metadata, dict)
            and started_metadata.get("story_category")
            == adventure.get("story_category")
            and started_metadata.get("lesson_topic") == adventure.get("lesson_topic")
            and started_metadata.get("client_uuid") == adventure.get("client_uuid"),
            "adventure_started metadata does not match the adventure row.",
        )

    return AuditResult(
        errors=errors,
        stored_chapter_count=len(chapters),
        summary_count=len(summaries) if isinstance(summaries, list) else 0,
        lesson_answer_count=len(answered_lessons),
        event_counts=event_counts,
    )


def fetch_records(
    client: Client, state_id: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    adventure_response = (
        client.table("adventures")
        .select(
            "id,user_id,client_uuid,state_data,story_category,lesson_topic,"
            "is_complete,completed_chapter_count,environment"
        )
        .eq("id", state_id)
        .limit(1)
        .execute()
    )
    adventure = adventure_response.data[0] if adventure_response.data else None
    telemetry_response = (
        client.table("telemetry_events")
        .select(
            "event_name,adventure_id,user_id,timestamp,metadata,environment,"
            "chapter_type,chapter_number,event_duration_seconds"
        )
        .eq("adventure_id", state_id)
        .order("timestamp")
        .execute()
    )
    return adventure, telemetry_response.data or []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Supabase persistence and telemetry after the live E2E journey."
    )
    parser.add_argument(
        "--state-id",
        required=True,
        help="The state_id from the Memory Lane summary URL.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        state_id = str(UUID(args.state_id))
    except ValueError:
        print("Supabase E2E audit: FAIL")
        print("- --state-id must be a UUID.")
        return 2

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not service_key:
        print("Supabase E2E audit: FAIL")
        print("- SUPABASE_URL and SUPABASE_SERVICE_KEY are required.")
        return 2

    try:
        client = create_client(supabase_url, service_key)
        adventure, events = fetch_records(client, state_id)
    except Exception as error:  # noqa: BLE001 - CLI boundary reports safe error type.
        print("Supabase E2E audit: FAIL")
        print(f"- Supabase query failed ({type(error).__name__}).")
        return 2

    result = audit_records(adventure, events, state_id=state_id)
    print(f"Supabase E2E audit: {'PASS' if result.passed else 'FAIL'}")
    print(
        "- Persistence: "
        f"{result.stored_chapter_count} stored chapters, "
        f"{result.summary_count} summaries, "
        f"{result.lesson_answer_count} lesson answers"
    )
    print(
        "- Telemetry: "
        + ", ".join(
            f"{name}={result.event_counts.get(name, 0)}"
            for name in REQUIRED_EVENT_NAMES
        )
    )
    for error in result.errors:
        print(f"- {error}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
