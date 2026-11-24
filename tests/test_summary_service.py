"""Behavioral + SQLite-backed contract tests for SummaryService."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    LessonResponse,
    StoryChoice,
)
from app.services.state_storage_service import StateStorageService
from app.services.summary import (
    AdventureSummaryDTO,
    ChapterTypeHelper,
    StateNotFoundError,
    SummaryGenerationError,
    SummaryService,
)
from tests.helpers.sqlite_state_storage import SQLiteAdventureStorage


def _chapter(
    number: int,
    chapter_type: ChapterType,
    *,
    question: dict[str, Any] | None = None,
    response: LessonResponse | None = None,
) -> ChapterData:
    content = f"Content for chapter {number}."
    choices = (
        [
            StoryChoice(text=f"Choice {index}", next_chapter=f"path-{index}")
            for index in range(1, 4)
        ]
        if chapter_type == ChapterType.STORY
        else []
    )
    return ChapterData(
        chapter_number=number,
        content=content,
        chapter_type=chapter_type,
        chapter_content=ChapterContent(content=content, choices=choices),
        question=question,
        response=response,
    )


@pytest.fixture
def sqlite_storage() -> Iterator[SQLiteAdventureStorage]:
    storage = SQLiteAdventureStorage()
    try:
        yield storage
    finally:
        storage.close()


@pytest.fixture
def summary_service(sqlite_storage: SQLiteAdventureStorage) -> SummaryService:
    return SummaryService(sqlite_storage)  # type: ignore[arg-type]


@pytest.fixture
def sample_state() -> AdventureState:
    question = {
        "question": "What did the explorer learn?",
        "chosen_answer": "Teamwork",
        "is_correct": True,
        "explanation": "The characters solved the problem together.",
    }
    return AdventureState(
        current_chapter_id="chapter-2",
        story_length=2,
        planned_chapter_types=[ChapterType.STORY, ChapterType.CONCLUSION],
        selected_narrative_elements={"settings": "Clockwork Sky City"},
        selected_sensory_details={"visuals": "Brass", "sounds": "Wind", "smells": "Pine"},
        selected_theme="Teamwork",
        selected_moral_teaching="Help one another",
        selected_plot_twist="A hidden compass appears",
        chapters=[
            _chapter(1, ChapterType.STORY),
            _chapter(2, ChapterType.CONCLUSION),
        ],
        chapter_summaries=["The journey begins.", "The journey concludes."],
        summary_chapter_titles=["A New Path", "Home Again"],
        lesson_questions=[question],
    )


def test_chapter_type_helper_normalizes_types() -> None:
    assert ChapterTypeHelper.get_chapter_type_string(ChapterType.STORY) == "story"
    assert ChapterTypeHelper.get_chapter_type_string("Lesson") == "lesson"
    assert ChapterTypeHelper.is_lesson_chapter("LESSON")
    assert ChapterTypeHelper.is_conclusion_chapter(ChapterType.CONCLUSION)


def test_adventure_summary_dto_converts_api_keys() -> None:
    dto = AdventureSummaryDTO(
        chapter_summaries=[{"number": 1, "chapter_type": "story"}],
        educational_questions=[{"user_answer": "Teamwork"}],
        statistics={"chapters_completed": 1},
    )

    assert dto.to_dict()["chapter_summaries"][0]["chapter_type"] == "story"
    assert dto.to_camel_case() == {
        "chapterSummaries": [{"number": 1, "chapterType": "story"}],
        "educationalQuestions": [{"userAnswer": "Teamwork"}],
        "statistics": {"chaptersCompleted": 1},
    }


@pytest.mark.asyncio
async def test_store_reconstruct_and_format_round_trip_in_sqlite(
    summary_service: SummaryService,
    sqlite_storage: SQLiteAdventureStorage,
    sample_state: AdventureState,
) -> None:
    user_id = UUID("76a9eb9e-6ab0-4a82-bd2b-18de95e79054")
    state_id = await summary_service.store_adventure_state(
        sample_state.model_dump(mode="json"),
        user_id=user_id,
    )

    reconstructed = await summary_service.get_adventure_state_from_id(state_id)
    formatted = await summary_service.format_adventure_summary_data(reconstructed)
    record = await sqlite_storage.get_adventure_record(state_id)

    assert record is not None
    assert record["user_id"] == str(user_id)
    assert [item["summary"] for item in formatted["chapter_summaries"]] == [
        "The journey begins.",
        "The journey concludes.",
    ]
    assert formatted["educational_questions"][0]["user_answer"] == "Teamwork"
    assert formatted["statistics"] == {
        "chapters_completed": 2,
        "questions_answered": 1,
        "time_spent": "-- mins",
        "correct_answers": 1,
    }


@pytest.mark.asyncio
async def test_get_adventure_state_raises_when_missing(
    summary_service: SummaryService,
) -> None:
    with pytest.raises(StateNotFoundError):
        await summary_service.get_adventure_state_from_id("missing-state")


def test_ensure_conclusion_marks_highest_numbered_chapter(
    summary_service: SummaryService,
) -> None:
    state = AdventureState(
        current_chapter_id="chapter-2",
        story_length=2,
        chapters=[_chapter(1, ChapterType.STORY), _chapter(2, ChapterType.STORY)],
    )

    result = summary_service.ensure_conclusion_chapter(state)

    assert result.chapters[-1].chapter_type == ChapterType.CONCLUSION


@pytest.mark.asyncio
async def test_store_adventure_state_wraps_storage_errors() -> None:
    failing_storage = MagicMock(spec=StateStorageService)
    failing_storage.store_state = AsyncMock(
        side_effect=RuntimeError("database unavailable")
    )
    service = SummaryService(failing_storage)

    with pytest.raises(SummaryGenerationError, match="database unavailable"):
        await service.store_adventure_state({"chapters": []})
