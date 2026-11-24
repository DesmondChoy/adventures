"""Exercise mutation response projection through the real Supabase SDK."""

from copy import deepcopy
import json
from types import SimpleNamespace
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
import pytest
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from app.services.state_storage_service import StateStorageService
from app.services.websocket.persistence import store_state_with_retry

ADVENTURE_ID = "00000000-0000-0000-0000-000000000010"
USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def storage_for(http_client):
    service = object.__new__(StateStorageService)
    service.supabase = create_client(
        "https://projection-test.invalid", "sb_secret_test-only",
        options=SyncClientOptions(httpx_client=http_client, persist_session=False,
                                  auto_refresh_token=False),
    )
    return service


@pytest.mark.parametrize("mode", ["update", "insert", "upsert"])
@pytest.mark.parametrize("outcome", ["success", "empty", "denied", "transport"])
async def test_projected_writes_preserve_payload_ownership_results_and_errors(mode, outcome):
    state = {"chapters": [{"chapter_number": 10, "chapter_type": "conclusion", "content": "Saved text"}],
             "metadata": {"story_category": "forest", "lesson_topic": "History", "client_uuid": "guest-id"}}
    original = deepcopy(state)
    requests = []
    response_sizes = []

    def handle(request):
        requests.append(request)
        assert request.headers["apikey"] == "sb_secret_test-only"
        if request.method == "GET":
            # Preserve the separate read used to abandon prior authenticated adventures.
            assert request.url.params["user_id"] == f"eq.{USER_ID}"
            return httpx.Response(200, json=[])
        assert request.url.params["select"] == "id"
        if outcome == "denied":
            return httpx.Response(403, json={"code": "42501", "message": "permission denied"})
        if outcome == "transport":
            raise httpx.ConnectError("network unavailable", request=request)
        response = httpx.Response(200, json=[{"id": ADVENTURE_ID}] if outcome == "success" else [])
        response_sizes.append(len(response.content))
        return response

    kwargs = {"user_id": USER_ID}
    if mode == "update":
        kwargs["adventure_id"] = ADVENTURE_ID
    elif mode == "upsert":
        kwargs["new_adventure_id"] = ADVENTURE_ID
    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        service = storage_for(http_client)
        if outcome == "success":
            assert await service.store_state(state, **kwargs) == ADVENTURE_ID
        elif outcome == "empty":
            with pytest.raises(ValueError) as error:
                await service.store_state(state, **kwargs)
            expected = (f"Failed to update adventure {ADVENTURE_ID}" if mode == "update"
                        else "Failed to store state: No data returned from Supabase")
            assert str(error.value) == expected
        elif outcome == "denied":
            with pytest.raises(APIError, match="permission denied"):
                await service.store_state(state, **kwargs)
        else:
            with pytest.raises(httpx.ConnectError, match="network unavailable"):
                await service.store_state(state, **kwargs)

    assert state == original
    writes = [request for request in requests if request.method != "GET"]
    assert len(writes) == 1
    assert len(requests) == (1 if mode == "update" else 2)
    request = writes[0]
    assert request.method == ("PATCH" if mode == "update" else "POST")
    payload = json.loads(request.content)
    assert payload["state_data"] == original
    assert payload["completed_chapter_count"] == 1
    assert payload["is_complete"] is True
    assert payload["user_id"] == str(USER_ID)
    assert payload["client_uuid"] == "guest-id"
    preferences = set(request.headers["Prefer"].split(","))
    assert "return=representation" in preferences
    if mode == "update":
        assert request.url.params["id"] == f"eq.{ADVENTURE_ID}"
        assert request.url.params["user_id"] == f"eq.{USER_ID}"
    else:
        assert payload["story_category"] == "forest"
        assert payload["lesson_topic"] == "History"
    if mode == "upsert":
        assert payload["id"] == ADVENTURE_ID
        assert request.url.params["on_conflict"] == "id"
        assert {"missing=default", "resolution=merge-duplicates"} <= preferences
    if response_sizes:
        assert max(response_sizes) <= 49


async def test_projected_creation_retry_keeps_one_preallocated_id():
    writes = []
    notifications = []

    async def send_json(payload):
        notifications.append(payload)

    def handle(request):
        assert request.url.params["select"] == "id"
        writes.append(json.loads(request.content))
        if len(writes) == 1:
            return httpx.Response(503, json={"code": "503", "message": "temporarily unavailable"})
        return httpx.Response(200, json=[{"id": writes[-1]["id"]}])

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        result = await store_state_with_retry(
            storage_for(http_client), SimpleNamespace(send_json=send_json),
            {"chapters": [], "metadata": {}}, operation="projection retry",
            retry_delay_seconds=0,
        )
    assert len(writes) == 2
    assert writes[0] == writes[1]
    assert result == writes[0]["id"]
    assert notifications == []
