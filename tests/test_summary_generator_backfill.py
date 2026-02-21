import pytest

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    LessonResponse,
)
from app.services.chapter_manager import ChapterManager
from app.services.websocket.summary_generator import ensure_all_summaries_exist


def _build_lesson_state(is_correct: bool = True) -> AdventureState:
    question = {
        "question": "What is 2 + 2?",
        "answers": [
            {"text": "4", "is_correct": True},
            {"text": "5", "is_correct": False},
        ],
    }
    chosen_answer = "4" if is_correct else "5"

    return AdventureState(
        current_chapter_id="chapter_1",
        chapters=[
            ChapterData(
                chapter_number=1,
                content="Lesson chapter content.",
                chapter_type=ChapterType.LESSON,
                response=LessonResponse(
                    question=question,
                    chosen_answer=chosen_answer,
                    is_correct=is_correct,
                ),
                chapter_content=ChapterContent(
                    content="Lesson chapter content.",
                    choices=[],
                ),
                question=question,
            )
        ],
        story_length=10,
        planned_chapter_types=[ChapterType.LESSON],
        selected_narrative_elements={"settings": "Forest"},
        selected_sensory_details={
            "visuals": "Moonlight",
            "sounds": "Wind",
            "smells": "Pine",
        },
        selected_theme="Friendship",
        selected_moral_teaching="Kindness matters",
        selected_plot_twist="A hidden map appears",
    )


@pytest.mark.asyncio
async def test_ensure_all_summaries_exist_handles_lesson_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _build_lesson_state(is_correct=True)
    observed: list[tuple[str | None, str]] = []

    async def fake_generate_chapter_summary(
        chapter_content: str,
        chosen_choice: str | None = None,
        choice_context: str = "",
    ) -> dict[str, str]:
        assert chapter_content == "Lesson chapter content."
        observed.append((chosen_choice, choice_context))
        return {"title": "Lesson 1", "summary": "Generated lesson summary"}

    monkeypatch.setattr(
        ChapterManager,
        "generate_chapter_summary",
        staticmethod(fake_generate_chapter_summary),
    )

    await ensure_all_summaries_exist(state)

    assert observed == [("4", " (Correct answer)")]
    assert state.chapter_summaries == ["Generated lesson summary"]
    assert state.summary_chapter_titles == ["Lesson 1"]
