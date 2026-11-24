"""Proof tests for structural invariants, state contracts, and formal-model bug replays."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.models.story import (
    AdventureState,
    ChapterContent,
    ChapterData,
    ChapterType,
    StoryChoice,
)
from app.routers import websocket_router
from app.services.adventure_state_manager import AdventureStateManager
from app.utils.static_assets import build_js_importmap, static_url
from tools.check_repo_invariants import (
    check_js_imports,
    check_python_invariants,
    check_templates,
    run_all_checks,
)


def _story_choices() -> list[StoryChoice]:
    return [
        StoryChoice(text=f"Choice {i}", next_chapter=f"path_{i}")
        for i in range(1, 4)
    ]


def test_current_repo_passes_all_invariant_checks() -> None:
    assert run_all_checks() == []


def test_js_invariant_catches_past_dual_module_version_bug(tmp_path: Path) -> None:
    # Replays commit 0ce4a5c: mismatched ?v= query strings on ES imports.
    js_file = tmp_path / "app/static/js/main.js"
    js_file.parent.mkdir(parents=True)
    js_file.write_text("import { showError } from './uiManager.js?v=20260221a';\n")

    violations = check_js_imports(tmp_path)

    assert len(violations) == 1
    assert "js-manual-version-query" in violations[0]
    assert "importmap" in violations[0]


def test_template_invariant_catches_manual_version_and_missing_asset(
    tmp_path: Path,
) -> None:
    tpl = tmp_path / "app/templates/base.html"
    tpl.parent.mkdir(parents=True)
    (tmp_path / "app/static/css").mkdir(parents=True)
    tpl.write_text(
        '<link rel="stylesheet" href="/static/css/theme.css?v=20260221a">\n'
        '<link rel="stylesheet" href="{{ static_url(\'css/missing.css\') }}">\n'
    )

    violations = check_templates(tmp_path)

    assert any("template-manual-version-query" in v for v in violations)
    assert any("static-asset-exists" in v for v in violations)


def test_python_invariants_catch_past_llm_bypass_eager_client_null_and_lock_bugs(
    tmp_path: Path,
) -> None:
    # Replays 5f07300 / 6c47d5a (LLM bypass), 3f1154b (eager client at import),
    # 5686fba (unchecked .maybe_single().execute().data), and bf68786 (unlocked summary write).
    ws_file = tmp_path / "app/services/websocket/broken.py"
    ws_file.parent.mkdir(parents=True)
    ws_file.write_text(
        "from app.services.llm.providers import GeminiService\n"
        "from app.services.telemetry_service import TelemetryService\n"
        "EAGER = TelemetryService()\n"
        "def bad(state, client):\n"
        "    llm = GeminiService()\n"
        "    row = client.table('adventures').select('*').maybe_single().execute().data\n"
        "    state.chapter_summaries.append('unlocked')\n"
        "    return llm, row\n"
    )

    violations = check_python_invariants(tmp_path)
    joined = "\n".join(violations)

    assert "llm-provider-bypass" in joined
    assert "LLMServiceFactory.create_for_use_case" in joined
    assert "eager-external-client-import" in joined
    assert "supabase-maybe-single-null-guard" in joined
    assert "summary-list-lock-discipline" in joined


def test_static_url_and_importmap_cover_all_js_modules() -> None:
    importmap = build_js_importmap()
    imports = importmap["imports"]

    assert "/static/js/main.js" in imports
    assert "/static/js/uiManager.js" in imports
    assert "/static/js/stateManager.js" in imports
    assert "/static/js/authManager.js" in imports
    assert imports["/static/js/uiManager.js"] == static_url("js/uiManager.js")
    assert "?v=" in imports["/static/js/uiManager.js"]


def test_adventure_state_enforces_custom_story_length_and_lowercase_chapter_types() -> None:
    assert ChapterType("STORY") is ChapterType.STORY
    assert ChapterType("Conclusion") is ChapterType.CONCLUSION

    chapters = [
        ChapterData(
            chapter_number=1,
            content="Opening.",
            chapter_type="STORY",
            chapter_content=ChapterContent(content="Opening.", choices=_story_choices()),
        ),
        ChapterData(
            chapter_number=2,
            content="Ending.",
            chapter_type="CONCLUSION",
            chapter_content=ChapterContent(content="Ending.", choices=[]),
        ),
        ChapterData(
            chapter_number=3,
            content="Overflow story.",
            chapter_type="STORY",
            chapter_content=ChapterContent(
                content="Overflow story.", choices=_story_choices()
            ),
        ),
    ]

    with pytest.raises(ValidationError, match="must be a SUMMARY chapter"):
        AdventureState(
            current_chapter_id="chapter_3",
            story_length=2,
            chapters=chapters,
            selected_narrative_elements={"settings": "Forest"},
            selected_sensory_details={"visuals": "V", "sounds": "S", "smells": "M"},
            selected_theme="T",
            selected_moral_teaching="M",
            selected_plot_twist="P",
        )


@pytest.mark.asyncio
async def test_all_persistent_adventure_state_fields_round_trip() -> None:
    original = AdventureState(
        current_chapter_id="chapter_2",
        story_length=2,
        planned_chapter_types=[ChapterType.STORY, ChapterType.CONCLUSION],
        current_storytelling_phase="Conclusion",
        selected_narrative_elements={
            "settings": "Clockwork Tower",
            "characters": "The Clockmaker",
            "objects": "Brass Compass",
            "events": "Comet Arrival",
        },
        selected_sensory_details={
            "visuals": "Brass gears",
            "sounds": "Ticking",
            "smells": "Ozone",
            "textures": "Cool metal",
        },
        selected_theme="Curiosity",
        selected_moral_teaching="Share knowledge",
        selected_plot_twist="The clockmaker is a time traveler",
        protagonist_description="A curious young inventor with brass goggles",
        protagonist_name="Mira",
        character_visuals={"Mira": "Brass goggles and teal scarf"},
        chapter_summaries=["Mira climbed the tower.", "Mira solved the riddle."],
        summary_chapter_titles=["The Tower", "The Riddle"],
        lesson_questions=[{"question": "Why?", "chosen_answer": "Because", "is_correct": True}],
        metadata={
            "story_category": "clockwork_sky_city",
            "lesson_topic": "Astronomy",
            "agency": {"name": "Star Compass", "references": []},
        },
        chapters=[
            ChapterData(
                chapter_number=1,
                content="Mira climbed the tower.",
                chapter_type=ChapterType.STORY,
                chapter_content=ChapterContent(
                    content="Mira climbed the tower.", choices=_story_choices()
                ),
            ),
            ChapterData(
                chapter_number=2,
                content="Mira solved the riddle.",
                chapter_type=ChapterType.CONCLUSION,
                chapter_content=ChapterContent(
                    content="Mira solved the riddle.", choices=[]
                ),
            ),
        ],
    )
    original.deferred_task_factories.append(lambda: None)
    _ = original.summary_lock
    _ = original.chapters_lock
    _ = original.character_visuals_lock

    dumped = original.model_dump(mode="json")
    assert "pending_background_tasks" not in dumped
    assert "deferred_task_factories" not in dumped
    assert all(ch["chapter_type"].islower() for ch in dumped["chapters"])
    assert all(ct.islower() for ct in dumped["planned_chapter_types"])

    reconstructed = await AdventureStateManager().reconstruct_state_from_storage(
        json.loads(json.dumps(dumped))
    )
    assert reconstructed is not None

    for field_name, field_info in AdventureState.model_fields.items():
        if field_info.exclude:
            continue
        assert getattr(reconstructed, field_name) == getattr(original, field_name), (
            f"Persistent AdventureState field `{field_name}` did not round-trip"
        )


@pytest.mark.asyncio
async def test_failed_initial_save_resets_state_so_retry_persists_adventure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replays TLA+ BugInitialSaveRetainedState counterexample against real router."""

    class _RetryWebSocket:
        def __init__(self) -> None:
            self.client = SimpleNamespace(host="formal-replay-client")
            self.json_messages: list[dict] = []
            self._incoming = [
                {"state": {"chapters": []}, "choice": "start"},
                {"state": {"chapters": []}, "choice": "start"},
            ]

        async def accept(self) -> None:
            return None

        async def close(self, **_kwargs: object) -> None:
            return None

        async def receive_json(self) -> dict:
            if self._incoming:
                return self._incoming.pop(0)
            raise RuntimeError("client closed")

        async def send_json(self, payload: dict) -> None:
            self.json_messages.append(payload)

        async def send_text(self, _text: str) -> None:
            return None

    store_calls: list[dict] = []
    persisted_adventure_ids: list[str] = []

    class _FlakyStorage:
        async def get_active_adventure_id(self, **_kwargs: object) -> None:
            return None

        async def store_state(self, _state_data: dict, **kwargs: object) -> str:
            store_calls.append(kwargs)
            if len(store_calls) <= 3:
                raise RuntimeError("transient outage on initial save")
            assigned = str(
                kwargs.get("adventure_id")
                or kwargs.get("new_adventure_id")
                or "recovered-id"
            )
            persisted_adventure_ids.append(assigned)
            return assigned

    async def fake_process_choice(**kwargs: object) -> tuple:
        state_manager = kwargs["state_manager"]
        state = state_manager.get_current_state()
        chapter = ChapterContent(content="Chapter one.", choices=_story_choices())
        state.chapters.append(
            ChapterData(
                chapter_number=1,
                content=chapter.content,
                chapter_type=ChapterType.STORY,
                chapter_content=chapter,
            )
        )
        return chapter, None, False, True

    async def fast_sleep(_delay: float) -> None:
        return None

    websocket = _RetryWebSocket()
    monkeypatch.setattr(websocket_router, "StateStorageService", _FlakyStorage)
    monkeypatch.setattr(
        websocket_router,
        "TelemetryService",
        lambda: SimpleNamespace(log_event=AsyncMock()),
    )
    monkeypatch.setattr(websocket_router, "process_choice", fake_process_choice)
    monkeypatch.setattr(websocket_router, "stream_chapter_content", AsyncMock())
    monkeypatch.setattr("app.services.websocket.persistence.asyncio.sleep", fast_sleep)

    await websocket_router.story_websocket(
        websocket=websocket,
        story_category="clockwork_sky_city",
        lesson_topic="Astronomy",
        client_uuid="guest-1",
        difficulty=None,
        token=None,
        resume_adventure_id=None,
    )

    message_types = [msg["type"] for msg in websocket.json_messages]
    assert "save_failed" in message_types
    assert "adventure_created" in message_types
    # 3 failed attempts on first start + 1 initial save on retry + 1 post-chapter progress save
    assert len(store_calls) == 5
    assert len(set(persisted_adventure_ids)) == 1
