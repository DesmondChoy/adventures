"""Unit tests for the current summary service contract."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
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
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=StateStorageService)
    storage.get_state = AsyncMock()
    storage.store_state = AsyncMock(return_value="test-state-id")
    return storage


@pytest.fixture
def summary_service(mock_storage: MagicMock) -> SummaryService:
    return SummaryService(mock_storage)


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


async def test_get_adventure_state_from_storage(
    summary_service: SummaryService,
    mock_storage: MagicMock,
    sample_state: AdventureState,
) -> None:
    mock_storage.get_state.return_value = {"stored": "state"}
    state_manager = MagicMock()
    state_manager.get_current_state.return_value = None
    state_manager.reconstruct_state_from_storage = AsyncMock(return_value=sample_state)

    with patch(
        "app.services.summary.service.AdventureStateManager",
        return_value=state_manager,
    ):
        result = await summary_service.get_adventure_state_from_id("test-state-id")

    assert result is sample_state
    mock_storage.get_state.assert_awaited_once_with("test-state-id")
    state_manager.reconstruct_state_from_storage.assert_awaited_once_with(
        {"stored": "state"}
    )


async def test_get_adventure_state_raises_when_missing(
    summary_service: SummaryService,
    mock_storage: MagicMock,
) -> None:
    mock_storage.get_state.return_value = None
    state_manager = MagicMock()
    state_manager.get_current_state.return_value = None

    with (
        patch(
            "app.services.summary.service.AdventureStateManager",
            return_value=state_manager,
        ),
        pytest.raises(StateNotFoundError),
    ):
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


async def test_format_adventure_summary_data(
    summary_service: SummaryService,
    sample_state: AdventureState,
) -> None:
    result = await summary_service.format_adventure_summary_data(sample_state)

    assert [item["summary"] for item in result["chapter_summaries"]] == [
        "The journey begins.",
        "The journey concludes.",
    ]
    assert result["educational_questions"][0]["user_answer"] == "Teamwork"
    assert result["statistics"] == {
        "chapters_completed": 2,
        "questions_answered": 1,
        "time_spent": "-- mins",
        "correct_answers": 1,
    }


async def test_store_adventure_state_uses_public_storage_contract(
    summary_service: SummaryService,
    mock_storage: MagicMock,
) -> None:
    user_id = UUID("76a9eb9e-6ab0-4a82-bd2b-18de95e79054")
    state_data: dict[str, Any] = {"chapters": [], "metadata": None}

    state_id = await summary_service.store_adventure_state(
        state_data,
        adventure_id="existing-id",
        user_id=user_id,
    )

    assert state_id == "test-state-id"
    assert state_data["chapter_summaries"] == []
    assert state_data["summary_chapter_titles"] == []
    assert state_data["metadata"] == {"user_id": str(user_id)}
    mock_storage.store_state.assert_awaited_once_with(
        state_data,
        adventure_id="existing-id",
        user_id=user_id,
    )


async def test_store_adventure_state_wraps_storage_errors(
    summary_service: SummaryService,
    mock_storage: MagicMock,
) -> None:
    mock_storage.store_state.side_effect = RuntimeError("database unavailable")

    with pytest.raises(SummaryGenerationError, match="database unavailable"):
        await summary_service.store_adventure_state({"chapters": []})
