"""Regression tests for read-only summary generation during storage."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.models.story import AdventureState, ChapterContent, ChapterData, ChapterType
from app.services.state_storage_service import StateStorageService
from app.services.summary import SummaryService


async def test_storage_does_not_synthesize_summary_content() -> None:
    storage = MagicMock(spec=StateStorageService)
    storage.store_state = AsyncMock(return_value="state-id")
    service = SummaryService(storage)
    state_data: dict[str, Any] = {
        "chapters": [{"chapter_number": 1, "content": "An opening scene."}],
        "lesson_questions": [],
    }

    await service.store_adventure_state(state_data)

    assert state_data["chapter_summaries"] == []
    assert state_data["summary_chapter_titles"] == []
    assert state_data["lesson_questions"] == []
    storage.store_state.assert_awaited_once_with(
        state_data,
        adventure_id=None,
        user_id=None,
    )


async def test_summary_display_uses_content_fallback_without_persisting() -> None:
    storage = MagicMock(spec=StateStorageService)
    service = SummaryService(storage)
    state = AdventureState(
        current_chapter_id="chapter-1",
        story_length=1,
        chapters=[
            ChapterData(
                chapter_number=1,
                content="The explorer solves the final puzzle.",
                chapter_type=ChapterType.CONCLUSION,
                chapter_content=ChapterContent(
                    content="The explorer solves the final puzzle.",
                    choices=[],
                ),
            )
        ],
    )

    result = await service.format_adventure_summary_data(state)

    assert result["chapter_summaries"][0]["summary"] == (
        "The explorer solves the final puzzle."
    )
    assert state.chapter_summaries == []
    assert state.summary_chapter_titles == []
    storage.store_state.assert_not_called()
