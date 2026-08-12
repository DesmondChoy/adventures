from types import SimpleNamespace
from typing import Any

import pytest

from app.services.state_storage_service import StateStorageService
from app.services.websocket.persistence import (
    STATE_SAVE_FAILED_MESSAGE,
    store_state_with_retry,
)


class _WebSocketRecorder:
    def __init__(self, fail_send: bool = False) -> None:
        self.fail_send = fail_send
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        if self.fail_send:
            raise RuntimeError("socket closed")
        self.messages.append(payload)


class _StorageRecorder:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls: list[dict[str, Any]] = []

    async def store_state(
        self,
        _state_data: dict[str, Any],
        **kwargs: Any,
    ) -> str:
        self.calls.append(kwargs)
        if len(self.calls) <= self.failures:
            raise RuntimeError("database unavailable")
        return kwargs.get("adventure_id") or kwargs["new_adventure_id"]


class _UpsertRecorder:
    def __init__(self) -> None:
        self.record: dict[str, Any] | None = None
        self.on_conflict: str | None = None
        self.default_to_null: bool | None = None

    def upsert(
        self,
        record: dict[str, Any],
        *,
        on_conflict: str,
        default_to_null: bool,
    ) -> "_UpsertRecorder":
        self.record = record
        self.on_conflict = on_conflict
        self.default_to_null = default_to_null
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=[self.record])


class _SupabaseRecorder:
    def __init__(self, query: _UpsertRecorder) -> None:
        self.query = query

    def table(self, table_name: str) -> _UpsertRecorder:
        assert table_name == "adventures"
        return self.query


@pytest.mark.asyncio
async def test_existing_state_save_retries_then_succeeds() -> None:
    storage = _StorageRecorder(failures=2)
    websocket = _WebSocketRecorder()

    state_id = await store_state_with_retry(
        storage,
        websocket,
        {"chapters": []},
        operation="chapter progress save",
        adventure_id="adventure-id",
        retry_delay_seconds=0,
    )

    assert state_id == "adventure-id"
    assert len(storage.calls) == 3
    assert websocket.messages == []


@pytest.mark.asyncio
async def test_new_state_save_reuses_preallocated_id_across_retries() -> None:
    storage = _StorageRecorder(failures=1)
    websocket = _WebSocketRecorder()

    state_id = await store_state_with_retry(
        storage,
        websocket,
        {"chapters": []},
        operation="initial adventure save",
        retry_delay_seconds=0,
    )

    generated_ids = {call["new_adventure_id"] for call in storage.calls}
    assert generated_ids == {state_id}
    assert len(storage.calls) == 2
    assert websocket.messages == []


@pytest.mark.asyncio
async def test_preallocated_new_adventure_id_uses_upsert() -> None:
    query = _UpsertRecorder()
    storage = object.__new__(StateStorageService)
    storage.supabase = _SupabaseRecorder(query)

    state_id = await storage.store_state(
        {"chapters": [], "metadata": {}},
        new_adventure_id="preallocated-id",
    )

    assert state_id == "preallocated-id"
    assert query.on_conflict == "id"
    assert query.default_to_null is False
    assert query.record is not None
    assert query.record["id"] == "preallocated-id"


@pytest.mark.asyncio
async def test_terminal_state_save_failure_notifies_client() -> None:
    storage = _StorageRecorder(failures=3)
    websocket = _WebSocketRecorder()

    state_id = await store_state_with_retry(
        storage,
        websocket,
        {"chapters": []},
        operation="chapter progress save",
        adventure_id="adventure-id",
        retry_delay_seconds=0,
    )

    assert state_id is None
    assert len(storage.calls) == 3
    assert websocket.messages == [
        {
            "type": "save_failed",
            "message": STATE_SAVE_FAILED_MESSAGE,
            "retryable": True,
        }
    ]


@pytest.mark.asyncio
async def test_terminal_failure_tolerates_closed_socket() -> None:
    storage = _StorageRecorder(failures=3)
    websocket = _WebSocketRecorder(fail_send=True)

    state_id = await store_state_with_retry(
        storage,
        websocket,
        {"chapters": []},
        operation="chapter progress save",
        adventure_id="adventure-id",
        retry_delay_seconds=0,
    )

    assert state_id is None
    assert len(storage.calls) == 3
