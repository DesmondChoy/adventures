import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import app.routers.websocket_router as websocket_router
import app.services.websocket.choice_processor as choice_processor
import app.services.websocket.core as websocket_core
import app.services.websocket.image_generator as image_generator
import app.services.websocket.stream_handler as stream_handler
from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    StoryChoice,
)
from app.routers.websocket_router import (
    _get_choice_id,
    _validate_adventure_ownership,
)
from app.services.adventure_state_manager import AdventureStateManager
from app.services.websocket.content_generator import parse_choice_text


class _DummyWebSocket:
    def __init__(self) -> None:
        self.client = SimpleNamespace(host="test-client")
        self.json_messages: list[dict[str, Any]] = []
        self.text_messages: list[str] = []

    async def accept(self) -> None:
        return None

    async def close(self, **_kwargs: Any) -> None:
        return None

    async def receive_json(self) -> dict[str, Any]:
        raise RuntimeError("test connection closed")

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.json_messages.append(payload)

    async def send_text(self, payload: str) -> None:
        self.text_messages.append(payload)


class _TelemetryRecorder:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def _story_choices() -> list[StoryChoice]:
    return [
        StoryChoice(text=f"Path {index}", next_chapter=f"path_{index}")
        for index in range(1, 4)
    ]


def _build_state(chapters: list[ChapterData]) -> AdventureState:
    return AdventureState(
        current_chapter_id="chapter_current",
        chapters=chapters,
        story_length=3,
        planned_chapter_types=[
            ChapterType.STORY,
            ChapterType.REFLECT,
            ChapterType.CONCLUSION,
        ],
        selected_narrative_elements={"settings": "Forest"},
        selected_sensory_details={
            "visuals": "Moonlight",
            "sounds": "Wind",
            "smells": "Pine",
        },
        selected_theme="Friendship",
        selected_moral_teaching="Kindness matters",
        selected_plot_twist="A hidden map appears",
        metadata={
            "story_category": "forest",
            "lesson_topic": "maps",
        },
    )


def test_adventure_ownership_uses_database_record_owner() -> None:
    owner_id = uuid4()
    adventure_record = {
        "user_id": str(owner_id),
        "state_data": {"metadata": {}},
    }

    assert _validate_adventure_ownership(
        adventure_record, owner_id, "adventure-id"
    )
    assert not _validate_adventure_ownership(
        adventure_record, uuid4(), "adventure-id"
    )
    assert not _validate_adventure_ownership(
        adventure_record, None, "adventure-id"
    )


@pytest.mark.asyncio
async def test_explicit_resume_rejects_mismatched_database_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_user_id = uuid4()
    database_owner_id = uuid4()
    resume_adventure_id = "adventure-id"
    stale_state_data = {
        "metadata": {"user_id": str(current_user_id)},
    }
    resumed_state = AdventureState(
        current_chapter_id="chapter_1",
        metadata={"story_category": "forest", "lesson_topic": "maps"},
    )
    manager = SimpleNamespace(
        reconstruct_state_from_storage=AsyncMock(return_value=resumed_state)
    )
    storage = SimpleNamespace(
        get_adventure_record=AsyncMock(
            return_value={
                "id": resume_adventure_id,
                "user_id": str(database_owner_id),
                "state_data": stale_state_data,
            }
        ),
        # HEAD reads this stale owner from state_data instead of the DB record.
        get_state=AsyncMock(return_value=stale_state_data),
        get_active_adventure_id=AsyncMock(return_value=None),
    )
    websocket = _DummyWebSocket()
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")
    monkeypatch.setattr(
        websocket_router.jwt,
        "decode",
        lambda *_args, **_kwargs: {"sub": str(current_user_id)},
    )
    monkeypatch.setattr(websocket_router, "AdventureStateManager", lambda: manager)
    monkeypatch.setattr(websocket_router, "StateStorageService", lambda: storage)
    monkeypatch.setattr(websocket_router, "TelemetryService", object)

    await websocket_router.story_websocket(
        websocket=websocket,
        story_category="forest",
        lesson_topic="maps",
        client_uuid=None,
        difficulty=None,
        token="test-token",
        resume_adventure_id=resume_adventure_id,
    )

    storage.get_adventure_record.assert_awaited_once_with(resume_adventure_id)
    manager.reconstruct_state_from_storage.assert_not_awaited()
    assert websocket.json_messages == [
        {
            "type": "adventure_status",
            "status": "new",
            "current_chapter": 1,
            "total_chapters": 10,
        }
    ]


@pytest.mark.asyncio
async def test_specific_resume_handshake_restores_conclusion_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_adventure_id = "adventure-id"
    conclusion = ChapterData(
        chapter_number=3,
        content="The adventure ends.",
        chapter_type=ChapterType.CONCLUSION,
        chapter_content=ChapterContent(
            content="The adventure ends.",
            choices=[],
        ),
    )
    state = _build_state(
        [
            ChapterData(
                chapter_number=1,
                content="The journey begins.",
                chapter_type=ChapterType.STORY,
                chapter_content=ChapterContent(
                    content="The journey begins.",
                    choices=_story_choices(),
                ),
            ),
            ChapterData(
                chapter_number=2,
                content="The journey continues.",
                chapter_type=ChapterType.REFLECT,
                chapter_content=ChapterContent(
                    content="The journey continues.",
                    choices=[],
                ),
            ),
            conclusion,
        ]
    )

    class FakeStateManager:
        async def reconstruct_state_from_storage(
            self,
            _stored_state: dict[str, Any],
        ) -> AdventureState:
            return state

        def get_current_state(self) -> AdventureState:
            return state

    class FakeStorage:
        async def get_adventure_record(
            self,
            adventure_id: str,
        ) -> dict[str, Any]:
            assert adventure_id == resume_adventure_id
            return {
                "id": adventure_id,
                "user_id": None,
                "client_uuid": "client-id",
                "state_data": state.model_dump(mode="json"),
            }

    class RouterWebSocket(_DummyWebSocket):
        def __init__(self) -> None:
            super().__init__()
            self.client = SimpleNamespace(host="conclusion-resume-test")
            self.messages = [
                {
                    "choice": "resume_specific_adventure",
                    "adventure_id_to_resume": resume_adventure_id,
                }
            ]

        async def accept(self) -> None:
            return None

        async def receive_json(self) -> dict[str, Any]:
            if self.messages:
                return self.messages.pop(0)
            raise RuntimeError("test connection closed")

        async def close(self, **_kwargs: Any) -> None:
            return None

    story_complete_calls: list[dict[str, Any]] = []

    async def fake_send_story_complete(**kwargs: Any) -> None:
        story_complete_calls.append(kwargs)

    websocket = RouterWebSocket()
    monkeypatch.setattr(
        websocket_router,
        "AdventureStateManager",
        FakeStateManager,
    )
    monkeypatch.setattr(websocket_router, "StateStorageService", FakeStorage)
    monkeypatch.setattr(websocket_router, "TelemetryService", object)
    monkeypatch.setattr(
        websocket_router,
        "send_story_complete",
        fake_send_story_complete,
    )

    await websocket_router.story_websocket(
        websocket=websocket,
        story_category="forest",
        lesson_topic="maps",
        client_uuid="client-id",
        difficulty=None,
        token=None,
        resume_adventure_id=resume_adventure_id,
    )

    assert len(story_complete_calls) == 1
    assert story_complete_calls[0]["state"] is state
    assert story_complete_calls[0]["already_streamed"] is False
    assert websocket.text_messages == []


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("start", "start"),
        ({"id": "start"}, "start"),
        ({"chosen_path": "start"}, "start"),
        ({"choice": "start"}, "start"),
        ({"choice": 1}, None),
    ],
)
def test_get_choice_id_normalizes_supported_payloads(
    payload: object, expected: str | None
) -> None:
    assert _get_choice_id(payload) == expected


@pytest.mark.asyncio
async def test_process_choice_accepts_choice_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _build_state([])
    state_manager = AdventureStateManager()
    state_manager.state = state
    websocket = _DummyWebSocket()
    expected = (None, None, False, False)
    observed: dict[str, Any] = {}

    async def fake_handle_reveal_summary(
        received_state: AdventureState,
        received_manager: AdventureStateManager,
        received_websocket: _DummyWebSocket,
        connection_data: dict[str, Any] | None,
    ) -> tuple[None, None, bool, bool]:
        observed.update(
            {
                "state": received_state,
                "manager": received_manager,
                "websocket": received_websocket,
                "connection_data": connection_data,
            }
        )
        return expected

    monkeypatch.setattr(
        websocket_core,
        "handle_reveal_summary",
        fake_handle_reveal_summary,
    )

    connection_data = {"adventure_id": "adventure-id"}
    result = await websocket_core.process_choice(
        state_manager=state_manager,
        choice_data={"choice": "reveal_summary"},
        story_category="forest",
        lesson_topic="maps",
        websocket=websocket,
        connection_data=connection_data,
    )

    assert result == expected
    assert observed == {
        "state": state,
        "manager": state_manager,
        "websocket": websocket,
        "connection_data": connection_data,
    }


@pytest.mark.parametrize(
    "choices_text",
    [
        "Choice A: Follow the river\nChoice B: Climb the hill\nChoice C: Wait",
        "Choice A: Follow the river. Choice B: Climb the hill. Choice C: Wait.",
    ],
)
def test_parse_choice_text_handles_multiline_and_single_line(
    choices_text: str,
) -> None:
    assert parse_choice_text(choices_text) == [
        "Follow the river" if "\n" in choices_text else "Follow the river.",
        "Climb the hill" if "\n" in choices_text else "Climb the hill.",
        "Wait" if "\n" in choices_text else "Wait.",
    ]


@pytest.mark.asyncio
async def test_direct_append_tracks_agency_references() -> None:
    first_chapter = ChapterData(
        chapter_number=1,
        content="The journey begins.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="The journey begins.",
            choices=_story_choices(),
        ),
    )
    state = _build_state([first_chapter])
    state.metadata["agency"] = {
        "type": "artifact",
        "name": "Compass",
        "references": [],
    }
    state_manager = AdventureStateManager()
    state_manager.state = state

    new_chapter = await stream_handler.create_and_append_chapter_direct(
        chapter_content=ChapterContent(
            content="The Compass points toward a hidden trail.",
            choices=[],
        ),
        chapter_type=ChapterType.REFLECT,
        sampled_question=None,
        state=state,
        state_manager=state_manager,
    )

    assert state.chapters[-1] is new_chapter
    assert state.metadata["agency"]["references"] == [
        {
            "chapter": 2,
            "has_reference": True,
            "chapter_type": ChapterType.REFLECT.value,
        }
    ]


@pytest.mark.asyncio
async def test_already_streamed_chapter_runs_post_stream_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_chapter = ChapterData(
        chapter_number=1,
        content="Previous chapter content.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="Previous chapter content.",
            choices=_story_choices(),
        ),
    )
    current_content = ChapterContent(
        content="Current chapter content.",
        choices=[],
    )
    current_chapter = ChapterData(
        chapter_number=2,
        content=current_content.content,
        chapter_type=ChapterType.REFLECT,
        chapter_content=current_content,
    )
    state = _build_state([first_chapter, current_chapter])
    websocket = _DummyWebSocket()
    telemetry = _TelemetryRecorder()
    observed: dict[str, Any] = {}
    state.deferred_task_factories.append(
        lambda: observed.update({"deferred_executed": True})
    )
    monkeypatch.setattr(
        stream_handler,
        "get_telemetry_service",
        lambda: telemetry,
    )

    connection_data: dict[str, Any] = {
        "adventure_id": str(uuid4()),
        "user_id": None,
    }
    await stream_handler.stream_chapter_content(
        websocket=websocket,
        state=state,
        adventure_id=connection_data["adventure_id"],
        story_category="forest",
        lesson_topic="maps",
        connection_data=connection_data,
        generated_chapter_content_model=current_content,
        already_streamed=True,
    )

    assert observed == {"deferred_executed": True}
    assert websocket.text_messages == []
    assert websocket.json_messages == [{"type": "hide_loader"}]
    assert connection_data["current_chapter_start_time_ms"] > 0
    assert state.metadata["chapter_2_start_time_ms"] == connection_data[
        "current_chapter_start_time_ms"
    ]
    assert telemetry.events[0]["event_name"] == "chapter_viewed"
    assert telemetry.events[0]["chapter_number"] == 2


@pytest.mark.asyncio
async def test_image_generation_uses_explicit_current_chapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_chapter = ChapterData(
        chapter_number=1,
        content="Previous chapter content.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="Previous chapter content.",
            choices=_story_choices(),
        ),
    )
    state = _build_state([previous_chapter])
    current_content = ChapterContent(
        content="Current chapter content.",
        choices=[],
    )
    observed: dict[str, Any] = {}

    async def fake_generate_image_scene(
        content: str,
        _character_visuals: dict[str, str],
    ) -> str:
        observed["scene_content"] = content
        return "Current scene"

    async def fake_synthesize_image_prompt(*_args: Any) -> str:
        return "Image prompt"

    async def fake_generate_image_async(prompt: str) -> str:
        observed["image_prompt"] = prompt
        return "image-data"

    fake_image_service = SimpleNamespace(
        synthesize_image_prompt=fake_synthesize_image_prompt,
        generate_image_async=fake_generate_image_async,
    )

    monkeypatch.setattr(
        image_generator.chapter_manager,
        "generate_image_scene",
        fake_generate_image_scene,
    )
    monkeypatch.setattr(
        image_generator,
        "get_image_service",
        lambda: fake_image_service,
    )

    image_tasks = await image_generator.start_image_generation_tasks(
        current_chapter_number=2,
        chapter_type=ChapterType.REFLECT,
        chapter_content=current_content,
        state=state,
    )
    await asyncio.gather(*(task for _, task in image_tasks))

    assert observed == {
        "scene_content": "Current chapter content.",
        "image_prompt": "Image prompt",
    }


@pytest.mark.asyncio
async def test_summary_storage_pads_titles_independently() -> None:
    chapter = ChapterData(
        chapter_number=1,
        content="Chapter content.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="Chapter content.",
            choices=_story_choices(),
        ),
    )
    state = _build_state([chapter])
    state.chapter_summaries = ["Existing summary"]
    state.summary_chapter_titles = []

    await choice_processor.store_chapter_summary(
        chapter,
        state,
        "Updated title",
        "Updated summary",
    )

    assert state.chapter_summaries == ["Updated summary"]
    assert state.summary_chapter_titles == ["Updated title"]


@pytest.mark.asyncio
async def test_background_summary_failure_fills_correct_chapter_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chapters = [
        ChapterData(
            chapter_number=1,
            content="Chapter one.",
            chapter_type=ChapterType.STORY,
            chapter_content=ChapterContent(
                content="Chapter one.",
                choices=_story_choices(),
            ),
        ),
        ChapterData(
            chapter_number=2,
            content="Chapter two.",
            chapter_type=ChapterType.REFLECT,
            chapter_content=ChapterContent(
                content="Chapter two.",
                choices=[],
            ),
        ),
        ChapterData(
            chapter_number=3,
            content="Chapter three.",
            chapter_type=ChapterType.CONCLUSION,
            chapter_content=ChapterContent(
                content="Chapter three.",
                choices=[],
            ),
        ),
    ]
    state = _build_state(chapters)

    async def fail_summary_generation(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        raise RuntimeError("summary unavailable")

    monkeypatch.setattr(
        choice_processor.chapter_manager,
        "generate_chapter_summary",
        fail_summary_generation,
    )

    await choice_processor.generate_chapter_summary_background(chapters[-1], state)

    assert state.chapter_summaries == [
        "Chapter summary not available",
        "Chapter summary not available",
        "Chapter summary not available",
    ]
    assert state.summary_chapter_titles == [
        "Chapter 1",
        "Chapter 2",
        "Chapter 3",
    ]


@pytest.mark.asyncio
async def test_background_summary_failure_preserves_existing_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chapter = ChapterData(
        chapter_number=1,
        content="Chapter one.",
        chapter_type=ChapterType.STORY,
        chapter_content=ChapterContent(
            content="Chapter one.",
            choices=_story_choices(),
        ),
    )
    state = _build_state([chapter])
    state.chapter_summaries = ["Existing summary"]
    state.summary_chapter_titles = ["Existing title"]

    async def fail_summary_generation(*_args: Any, **_kwargs: Any) -> dict[str, str]:
        raise RuntimeError("summary unavailable")

    monkeypatch.setattr(
        choice_processor.chapter_manager,
        "generate_chapter_summary",
        fail_summary_generation,
    )

    await choice_processor.generate_chapter_summary_background(chapter, state)

    assert state.chapter_summaries == ["Existing summary"]
    assert state.summary_chapter_titles == ["Existing title"]

    state.chapter_summaries = ["Chapter summary not available"]
    await choice_processor.generate_chapter_summary_background(chapter, state)

    assert state.chapter_summaries == ["Chapter summary not available"]
    assert state.summary_chapter_titles == ["Existing title"]


@pytest.mark.asyncio
async def test_conclusion_summary_update_keeps_authenticated_owner_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conclusion = ChapterData(
        chapter_number=3,
        content="The adventure ends.",
        chapter_type=ChapterType.CONCLUSION,
        chapter_content=ChapterContent(
            content="The adventure ends.",
            choices=[],
        ),
    )
    state = _build_state(
        [
            ChapterData(
                chapter_number=1,
                content="The journey begins.",
                chapter_type=ChapterType.STORY,
                chapter_content=ChapterContent(
                    content="The journey begins.",
                    choices=_story_choices(),
                ),
            ),
            ChapterData(
                chapter_number=2,
                content="The journey continues.",
                chapter_type=ChapterType.REFLECT,
                chapter_content=ChapterContent(
                    content="The journey continues.",
                    choices=[],
                ),
            ),
            conclusion,
        ]
    )
    websocket = _DummyWebSocket()
    user_id = uuid4()
    observed: dict[str, Any] = {}

    async def fake_generate_chapter_summary(
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, str]:
        return {"title": "The End", "summary": "A complete adventure."}

    async def fake_store_state(
        state_data: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        observed["state_data"] = state_data
        observed.update(kwargs)
        return "adventure-id"

    fake_state_storage_service = SimpleNamespace(store_state=fake_store_state)

    monkeypatch.setattr(
        choice_processor.chapter_manager,
        "generate_chapter_summary",
        fake_generate_chapter_summary,
    )
    monkeypatch.setattr(
        choice_processor,
        "get_state_storage_service",
        lambda: fake_state_storage_service,
    )

    state_id = await choice_processor.generate_conclusion_chapter_summary(
        conclusion_chapter=conclusion,
        state=state,
        websocket=websocket,
        connection_data={
            "adventure_id": "adventure-id",
            "user_id": user_id,
        },
        send_ready_signal=False,
    )

    assert state_id == "adventure-id"
    assert observed["adventure_id"] == "adventure-id"
    assert observed["user_id"] == user_id
    assert observed["explicit_is_complete"] is True
    assert state.chapter_summaries[2] == "A complete adventure."
    assert state.summary_chapter_titles[2] == "The End"
