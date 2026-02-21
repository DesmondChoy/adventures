import pytest

from app.models.story import AdventureState, ChapterContent, ChapterType, LessonResponse
import app.services.websocket.stream_handler as stream_handler


class _DummyWebSocket:
    def __init__(self) -> None:
        self.json_messages = []

    async def send_json(self, payload):
        self.json_messages.append(payload)

    async def send_text(self, _text: str) -> None:
        return None


def _build_state(chapter_type: ChapterType) -> AdventureState:
    return AdventureState(
        current_chapter_id="chapter_0",
        chapters=[],
        story_length=10,
        planned_chapter_types=[chapter_type],
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
@pytest.mark.parametrize(
    "chapter_type",
    [ChapterType.STORY, ChapterType.LESSON, ChapterType.CONCLUSION],
)
async def test_live_generation_passes_previous_lessons_for_non_reflect_chapters(
    monkeypatch: pytest.MonkeyPatch,
    chapter_type: ChapterType,
) -> None:
    state = _build_state(chapter_type)
    websocket = _DummyWebSocket()

    previous_lessons = [
        LessonResponse(
            question={
                "question": "What is 2 + 2?",
                "answers": [{"text": "4", "is_correct": True}],
            },
            chosen_answer="4",
            is_correct=True,
        )
    ]

    call_data = {
        "collect_called": 0,
        "passed_previous_lessons": None,
    }

    async def fake_load_story_config(_story_category: str):
        return {"name": "Test Story"}

    async def fake_load_lesson_question(_lesson_topic: str, _state: AdventureState):
        return {
            "question": "What is 3 + 3?",
            "answers": [{"text": "6", "is_correct": True}],
        }

    def fake_collect_previous_lessons(_state: AdventureState):
        call_data["collect_called"] += 1
        return previous_lessons

    async def fake_generate_chapter_content_with_retries(**kwargs):
        call_data["passed_previous_lessons"] = kwargs["previous_lessons"]
        return ChapterContent(content="Generated chapter", choices=[])

    async def fake_send_chapter_data(*_args, **_kwargs):
        return None

    async def fake_stream_text_content(*_args, **_kwargs):
        return None

    async def fake_execute_deferred_task_factories(*_args, **_kwargs):
        return None

    async def fake_start_image_generation_tasks(*_args, **_kwargs):
        return []

    async def fake_process_image_tasks(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.websocket.content_generator.load_story_config",
        fake_load_story_config,
    )
    monkeypatch.setattr(
        "app.services.websocket.content_generator.load_lesson_question",
        fake_load_lesson_question,
    )
    monkeypatch.setattr(
        "app.services.websocket.content_generator.collect_previous_lessons",
        fake_collect_previous_lessons,
    )
    monkeypatch.setattr(
        "app.services.websocket.content_generator.generate_chapter_content_with_retries",
        fake_generate_chapter_content_with_retries,
    )
    monkeypatch.setattr(stream_handler, "send_chapter_data", fake_send_chapter_data)
    monkeypatch.setattr(stream_handler, "stream_text_content", fake_stream_text_content)
    monkeypatch.setattr(
        stream_handler,
        "execute_deferred_task_factories",
        fake_execute_deferred_task_factories,
    )
    monkeypatch.setattr(
        "app.services.websocket.image_generator.start_image_generation_tasks",
        fake_start_image_generation_tasks,
    )
    monkeypatch.setattr(
        "app.services.websocket.image_generator.process_image_tasks",
        fake_process_image_tasks,
    )

    await stream_handler.stream_chapter_with_live_generation(
        story_category="test-story",
        lesson_topic="test-topic",
        state=state,
        websocket=websocket,
        state_manager=None,
    )

    assert call_data["collect_called"] == 1
    assert call_data["passed_previous_lessons"] is previous_lessons
