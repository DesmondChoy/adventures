"""Behavioral WebSocket streaming tests across real loaders, validation, and protocol code.

Stubs only external LLM and image provider boundaries so assertions verify
observable WebSocket frames and outbound LLM requests rather than internal helpers.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    LessonResponse,
)
from app.services.llm.chapter_output import GeneratedChapter
from app.services.websocket import content_generator, image_generator, stream_handler


class _RecordingWebSocket:
    def __init__(self) -> None:
        self.frames: list[tuple[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.frames.append(("json", payload))

    async def send_text(self, text: str) -> None:
        self.frames.append(("text", text))


class _RecordingLLMService:
    def __init__(self, chapter_type: ChapterType) -> None:
        self.chapter_type = chapter_type
        self.requests: list[dict[str, Any]] = []

    async def generate_structured_chapter(
        self,
        *,
        story_config: dict[str, Any],
        state: AdventureState,
        question: dict[str, Any] | None,
        previous_lessons: list[LessonResponse],
        context: dict[str, Any] | None = None,
    ) -> GeneratedChapter:
        self.requests.append(
            {
                "story_config": story_config,
                "state": state,
                "question": question,
                "previous_lessons": list(previous_lessons),
                "context": context,
            }
        )
        if self.chapter_type in (ChapterType.STORY, ChapterType.REFLECT):
            return GeneratedChapter(
                content="A bright brass compass points toward the observatory.",
                choices=(
                    "Climb the copper stairs to the dome",
                    "Inspect the star chart on the workbench",
                    "Ask the clockmaker about the comet",
                ),
            )
        return GeneratedChapter(
            content="The observatory dome opens to reveal the constellations.",
            choices=(),
        )


def _state_with_prior_lesson(next_type: ChapterType) -> AdventureState:
    prior_question = {
        "question": "Which planet is famous for its icy rings?",
        "answers": [
            {"text": "Saturn", "is_correct": True},
            {"text": "Mercury", "is_correct": False},
        ],
        "explanation": "Saturn's rings are made of ice and rock.",
    }
    prior_lesson_chapter = ChapterData(
        chapter_number=1,
        content="The brass telescope focuses on a ringed planet.",
        chapter_type=ChapterType.LESSON,
        question=prior_question,
        response=LessonResponse(
            question=prior_question,
            chosen_answer="Saturn",
            is_correct=True,
        ),
        chapter_content=ChapterContent(
            content="The brass telescope focuses on a ringed planet.",
            choices=[],
        ),
    )
    return AdventureState(
        current_chapter_id="chapter_1",
        chapters=[prior_lesson_chapter],
        story_length=3,
        planned_chapter_types=[ChapterType.LESSON, next_type, ChapterType.CONCLUSION],
        selected_narrative_elements={"settings": "Clockwork Observatory"},
        selected_sensory_details={
            "visuals": "Brass gears",
            "sounds": "Soft ticking",
            "smells": "Warm oil",
        },
        selected_theme="Curiosity",
        selected_moral_teaching="Ask questions carefully",
        selected_plot_twist="The sky map hides a secret route",
        protagonist_name="Mira",
        protagonist_description="A curious young explorer with brass goggles",
        metadata={"story_category": "clockwork_sky_city", "lesson_topic": "Astronomy"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chapter_type",
    [ChapterType.STORY, ChapterType.LESSON, ChapterType.CONCLUSION],
)
async def test_live_generation_sends_prior_lessons_to_llm_and_orders_ws_frames(
    monkeypatch: pytest.MonkeyPatch,
    chapter_type: ChapterType,
) -> None:
    state = _state_with_prior_lesson(chapter_type)
    websocket = _RecordingWebSocket()
    llm_service = _RecordingLLMService(chapter_type)

    async def no_images(*_args: Any, **_kwargs: Any) -> list[Any]:
        return []

    monkeypatch.setattr(content_generator, "get_llm_service", lambda: llm_service)
    monkeypatch.setattr(image_generator, "start_image_generation_tasks", no_images)
    monkeypatch.setattr(stream_handler, "WORD_DELAY", 0)
    monkeypatch.setattr(stream_handler, "PARAGRAPH_DELAY", 0)

    await stream_handler.stream_chapter_with_live_generation(
        story_category="clockwork_sky_city",
        lesson_topic="Astronomy",
        state=state,
        websocket=websocket,
        state_manager=None,
    )

    assert len(llm_service.requests) == 1
    prior_lessons = llm_service.requests[0]["previous_lessons"]
    assert len(prior_lessons) == 1
    assert prior_lessons[0].question["question"] == "Which planet is famous for its icy rings?"
    assert prior_lessons[0].chosen_answer == "Saturn"

    first_chapter_update = next(
        idx
        for idx, (kind, payload) in enumerate(websocket.frames)
        if kind == "json" and payload.get("type") == "chapter_update"
    )
    first_text = next(
        idx for idx, (kind, _payload) in enumerate(websocket.frames) if kind == "text"
    )
    assert first_chapter_update < first_text

    choices_frames = [
        payload
        for kind, payload in websocket.frames
        if kind == "json" and payload.get("type") == "choices"
    ]
    if chapter_type == ChapterType.STORY:
        assert len(choices_frames) == 1
        assert len(choices_frames[0]["choices"]) == 3
    elif chapter_type == ChapterType.LESSON:
        assert len(choices_frames) == 1
        assert len(choices_frames[0]["choices"]) >= 2
    else:
        assert choices_frames == []
