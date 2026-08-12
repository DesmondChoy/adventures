"""Regression test for duplicate state IDs on the Memory Lane endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.models.story import AdventureState, ChapterContent, ChapterData, ChapterType
from app.routers.summary_router import get_adventure_summary
from app.services.summary import SummaryService


async def test_summary_endpoint_normalizes_duplicate_state_id() -> None:
    state_id = "36d9319b-02c7-47c9-b0a4-99657dd99016"
    state = AdventureState(
        current_chapter_id="chapter-1",
        story_length=1,
        chapters=[
            ChapterData(
                chapter_number=1,
                content="The adventure reaches its conclusion.",
                chapter_type=ChapterType.CONCLUSION,
                chapter_content=ChapterContent(
                    content="The adventure reaches its conclusion.",
                    choices=[],
                ),
            )
        ],
    )

    storage = MagicMock()
    storage.get_adventure_record = AsyncMock(
        return_value={"state_data": {"chapters": []}, "user_id": None}
    )
    service = SummaryService(storage)
    service.get_adventure_state_from_id = AsyncMock(return_value=state)
    service.ensure_conclusion_chapter = MagicMock(return_value=state)
    service.format_adventure_summary_data = AsyncMock(
        return_value={
            "chapter_summaries": [
                {
                    "number": 1,
                    "chapter_type": "conclusion",
                    "summary": "The adventure ends.",
                }
            ],
            "educational_questions": [],
            "statistics": {"chapters_completed": 1},
        }
    )

    telemetry_query = MagicMock()
    telemetry_query.select.return_value = telemetry_query
    telemetry_query.eq.return_value = telemetry_query
    telemetry_query.gte.return_value = telemetry_query
    telemetry_query.execute.return_value = MagicMock(data=[{"id": "recent-event"}])
    telemetry = MagicMock()
    telemetry.supabase.table.return_value = telemetry_query

    with patch(
        "app.routers.summary_router.get_telemetry_service",
        return_value=telemetry,
    ):
        result = await get_adventure_summary(
            state_id=f"{state_id},{state_id}",
            user_id=None,
            summary_service=service,
        )

    storage.get_adventure_record.assert_awaited_once_with(state_id)
    service.get_adventure_state_from_id.assert_awaited_once_with(state_id)
    service.format_adventure_summary_data.assert_awaited_once_with(state, state_id)
    assert result["chapterSummaries"][0]["chapterType"] == "conclusion"
    assert result["statistics"]["chaptersCompleted"] == 1
