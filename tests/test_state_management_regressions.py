import pytest

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    StoryChoice,
)
from app.services.adventure_state_manager import AdventureStateManager


def _lesson_chapter(number: int, content: str) -> ChapterData:
    return ChapterData(
        chapter_number=number,
        content=content,
        chapter_type=ChapterType.LESSON,
        chapter_content=ChapterContent(content=content, choices=[]),
    )


@pytest.mark.asyncio
async def test_reconstruction_preserves_character_visual_state() -> None:
    chapter = ChapterData(
        chapter_number=1,
        content="The journey begins.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="The journey begins.",
            choices=[
                StoryChoice(text=f"Choice {index}", next_chapter=f"path_{index}")
                for index in range(1, 4)
            ],
        ),
    )
    original_state = AdventureState(
        current_chapter_id="chapter_1",
        story_length=10,
        selected_narrative_elements={"settings": "Forest"},
        selected_sensory_details={
            "visuals": "Green light",
            "sounds": "Birdsong",
            "smells": "Pine",
        },
        selected_theme="Courage",
        selected_moral_teaching="Ask for help",
        selected_plot_twist="The guide knew the path",
        protagonist_description="A child in a red raincoat",
        character_visuals={"Mina": "A child in a red raincoat"},
        chapters=[chapter],
        planned_chapter_types=[
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.REFLECT,
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.STORY,
            ChapterType.STORY,
            ChapterType.CONCLUSION,
        ],
        current_storytelling_phase="Rising",
    )

    state = await AdventureStateManager().reconstruct_state_from_storage(
        original_state.model_dump(mode="json")
    )

    assert state is not None
    assert state.protagonist_description == "A child in a red raincoat"
    assert state.character_visuals == {"Mina": "A child in a red raincoat"}


def test_agency_reference_tracking_uses_the_selected_agency() -> None:
    state = AdventureState(
        current_chapter_id="chapter_2",
        metadata={
            "agency": {
                "name": "Silver Compass",
                "type": "choice",
                "references": [],
            }
        },
    )
    manager = AdventureStateManager()
    manager.state = state

    manager.update_agency_references(
        _lesson_chapter(1, "The hero faced a difficult choice.")
    )
    manager.update_agency_references(
        _lesson_chapter(2, "The Silver Compass pointed toward home.")
    )

    assert [
        reference["has_reference"]
        for reference in state.metadata["agency"]["references"]
    ] == [False, True]


def test_plot_twist_validation_is_idempotent_per_chapter() -> None:
    state = AdventureState(
        current_chapter_id="chapter_2",
        current_storytelling_phase="Rising",
        selected_plot_twist="A hidden map appears",
    )
    manager = AdventureStateManager()
    manager.state = state
    chapter = {"chapter_number": 1, "content": "A compass glowed."}

    manager.validate_plot_twist_progression(chapter)
    manager.validate_plot_twist_progression(chapter)

    assert state.metadata["previous_hints"] == ["A compass glowed."]
    assert state.metadata["plot_twist_validated_chapters"] == [1]
