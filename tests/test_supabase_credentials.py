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
