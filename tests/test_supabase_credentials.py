import logging
from uuid import UUID

import httpx
import pytest
from supabase.lib.client_options import SyncClientOptions

from supabase import create_client


@pytest.mark.parametrize("key", ["sb_publishable_test-only", "sb_secret_test-only"])
def test_sdk_accepts_opaque_api_key_and_uses_it_on_mocked_request(key):
    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["apikey"] == key
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        client = create_client(
            "https://configured-project.example",
            key,
            options=SyncClientOptions(
                httpx_client=http_client,
                persist_session=False,
                auto_refresh_token=False,
            ),
        )
        assert client.table("adventures").select("id").limit(1).execute().data == []
    assert len(requests) == 1
    assert requests[0].url.host == "configured-project.example"


def test_backend_services_construct_real_clients_with_opaque_secret_key(monkeypatch):
    from app.services import feedback_service, state_storage_service, telemetry_service

    key = "sb_secret_backend-test-only"
    monkeypatch.setenv("SUPABASE_URL", "https://configured-project.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", key)
    monkeypatch.setattr(state_storage_service.StateStorageService, "_instance", None)
    for module in [feedback_service, state_storage_service, telemetry_service]:
        monkeypatch.setattr(module, "load_dotenv", lambda: False)

    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["apikey"] == key
        return httpx.Response(200, json=[])

    for factory in [
        state_storage_service.StateStorageService,
        feedback_service.FeedbackService,
        telemetry_service.TelemetryService,
    ]:
        service = factory()
        with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
            service.supabase.options.httpx_client = http_client
            assert (
                service.supabase.table("adventures")
                .select("id")
                .limit(1)
                .execute()
                .data
                == []
            )
    assert len(requests) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("get_state", ("test-adventure",)),
        ("get_adventure_record", ("test-adventure",)),
        (
            "get_user_current_adventure_for_resume",
            (UUID("00000000-0000-0000-0000-000000000001"),),
        ),
        ("get_active_adventure_by_client_uuid", ("test-client",)),
        (
            "get_active_adventure_by_client_uuid_for_user",
            ("test-client", UUID("00000000-0000-0000-0000-000000000001")),
        ),
    ],
)
@pytest.mark.parametrize("outcome", ["missing", "found", "denied"])
async def test_optional_single_storage_reads(method, args, outcome, caplog):
    from app.services.state_storage_service import StateStorageService

    record = {
        "id": "test-adventure",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "client_uuid": "test-client",
        "state_data": {"chapters": [], "metadata": {}},
    }
    requests = []

    def handle(request):
        requests.append(request)
        assert request.headers["apikey"] == "sb_secret_storage-test-only"
        if outcome == "denied":
            return httpx.Response(
                403,
                json={"code": "42501", "message": "permission denied"},
            )
        return httpx.Response(200, json=[record] if outcome == "found" else [])

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        storage = object.__new__(StateStorageService)
        storage.supabase = create_client(
            "https://configured-project.example",
            "sb_secret_storage-test-only",
            options=SyncClientOptions(
                httpx_client=http_client,
                persist_session=False,
                auto_refresh_token=False,
            ),
        )
        with caplog.at_level(logging.ERROR, logger="story_app"):
            result = await getattr(storage, method)(*args)

    if outcome == "found":
        assert result == (record["state_data"] if method == "get_state" else record)
    else:
        assert result is None
    assert len(requests) == 1
    assert requests[0].url.path == "/rest/v1/adventures"
    errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert bool(errors) == (outcome == "denied")
