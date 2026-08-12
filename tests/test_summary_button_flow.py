"""Offline integration test for the Memory Lane summary flow."""

from unittest.mock import MagicMock

from app.models.story import ChapterType
from app.services.adventure_state_manager import AdventureStateManager
from app.services.state_storage_service import StateStorageService
from app.services.summary import SummaryService
from tests.utils.generate_test_state import generate_test_state


async def test_generated_state_reconstructs_and_formats_for_memory_lane() -> None:
    stored_state = await generate_test_state(use_mock=True)
    state = await AdventureStateManager().reconstruct_state_from_storage(stored_state)
    assert state is not None

    service = SummaryService(MagicMock(spec=StateStorageService))
    state = service.ensure_conclusion_chapter(state)
    summary = await service.format_adventure_summary_data(state)

    assert len(summary["chapter_summaries"]) == state.story_length
    assert summary["chapter_summaries"][-1]["chapter_type"] == "conclusion"
    assert summary["educational_questions"]
    assert summary["statistics"]["chapters_completed"] == state.story_length
    assert state.chapters[-1].chapter_type == ChapterType.CONCLUSION
