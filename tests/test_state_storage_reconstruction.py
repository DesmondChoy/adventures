"""Regression tests for reconstructing serialized adventure state."""

from copy import deepcopy

from app.models.story import ChapterType
from app.services.adventure_state_manager import AdventureStateManager
from tests.utils.generate_test_state import generate_test_state


async def test_reconstruction_normalizes_uppercase_chapter_types() -> None:
    stored_state = deepcopy(await generate_test_state(use_mock=True))
    stored_state["planned_chapter_types"] = [
        chapter_type.upper() for chapter_type in stored_state["planned_chapter_types"]
    ]
    for chapter in stored_state["chapters"]:
        chapter["chapter_type"] = chapter["chapter_type"].upper()

    state = await AdventureStateManager().reconstruct_state_from_storage(stored_state)

    assert state is not None
    assert all(
        isinstance(chapter.chapter_type, ChapterType) for chapter in state.chapters
    )
    assert all(
        isinstance(chapter_type, ChapterType)
        for chapter_type in state.planned_chapter_types
    )
    assert state.chapters[-1].chapter_type == ChapterType.CONCLUSION


async def test_reconstruction_supplies_required_defaults() -> None:
    stored_state = deepcopy(await generate_test_state(use_mock=True))
    stored_state.pop("selected_narrative_elements")
    stored_state.pop("selected_sensory_details")
    stored_state.pop("planned_chapter_types")

    state = await AdventureStateManager().reconstruct_state_from_storage(stored_state)

    assert state is not None
    assert state.selected_narrative_elements["settings"] == "Default Setting"
    assert state.selected_sensory_details["visuals"] == "Default Visual"
    assert len(state.planned_chapter_types) == state.story_length
