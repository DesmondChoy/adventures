import base64
import json
from uuid import uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.auth import supabase_auth
from app.auth.dependencies import get_current_user_id, get_current_user_id_optional

REAL_ASYNC_CLIENT = httpx.AsyncClient
AUTH_URL = "https://configured-project.example/auth/v1/user"
PUBLISHABLE_KEY = "sb_publishable_test-only"


@pytest.fixture
def auth_transport(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://configured-project.example/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", PUBLISHABLE_KEY)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "unused-test-secret")
    requests = []
    options = []

    def install(handler):
        def record(request):
            requests.append(request)
            return handler(request)

        def client_factory(**kwargs):
            options.append(kwargs)
            return REAL_ASYNC_CLIENT(transport=httpx.MockTransport(record), **kwargs)

        monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", client_factory)
        return requests, options

    return install


def auth_app():
    app = FastAPI()

    @app.get("/optional")
    async def optional(user_id=Depends(get_current_user_id_optional)):
        return {"user_id": str(user_id) if user_id else None}

    @app.get("/required")
    async def required(user_id=Depends(get_current_user_id)):
        return {"user_id": str(user_id)}

    return app


def untrusted_token(subject):
    def encode(value):
        return (
            base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
        )

    return ".".join(
        [
            encode({"alg": "HS256"}),
            encode({"sub": str(subject), "iss": "https://untrusted.example"}),
            "untrusted-signature",
        ]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("anonymous", [False, True])
async def test_user_identity_comes_only_from_configured_auth_response(
    auth_transport, anonymous
):
    user_id = uuid4()
    token = untrusted_token(uuid4())
    requests, options = auth_transport(
        lambda _request: httpx.Response(
            200, json={"id": str(user_id), "is_anonymous": anonymous}
        )
    )
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/required", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert response.json() == {"user_id": str(user_id)}
    assert len(requests) == 1
    assert str(requests[0].url) == AUTH_URL
    assert requests[0].headers["apikey"] == PUBLISHABLE_KEY
    assert requests[0].headers["authorization"] == f"Bearer {token}"
    assert options == [
        {"timeout": supabase_auth.AUTH_TIMEOUT_SECONDS, "follow_redirects": False}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("path, status", [("/optional", 200), ("/required", 401)])
async def test_missing_token_preserves_explicit_optional_guest_path(
    auth_transport, path, status
):
    requests, _ = auth_transport(
        lambda _request: pytest.fail("Guest requested authentication")
    )
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(path)
    assert response.status_code == status
    if status == 200:
        assert response.json() == {"user_id": None}
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header", ["", "Basic test", "Bearer ", "Bearer two tokens", b"Bearer \xe9"]
)
async def test_malformed_supplied_token_never_becomes_guest(auth_transport, header):
    requests, _ = auth_transport(
        lambda _request: pytest.fail("Malformed credentials reached Auth")
    )
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get("/optional", headers={"Authorization": header})
    assert response.status_code == 401
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "upstream_status, expected", [(401, 401), (403, 401), (500, 503), (307, 503)]
)
async def test_auth_rejection_or_failure_never_becomes_guest(
    auth_transport, upstream_status, expected, caplog
):
    token = "rejected-token-test-only"
    requests, _ = auth_transport(
        lambda _request: httpx.Response(
            upstream_status,
            text="private-upstream-body",
            headers={"Location": "https://untrusted.example"},
        )
    )
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/optional", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == expected
    assert len(requests) == 1
    for private_value in [token, PUBLISHABLE_KEY, "private-upstream-body"]:
        assert private_value not in caplog.text


@pytest.mark.asyncio
async def test_auth_timeout_fails_closed(auth_transport):
    def timeout(request):
        raise httpx.ReadTimeout("test timeout", request=request)

    auth_transport(timeout)
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/optional", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [{}, {"id": "not-a-uuid"}, {"sub": str(uuid4())}, [], None]
)
async def test_auth_requires_response_user_uuid(auth_transport, body):
    auth_transport(lambda _request: httpx.Response(200, json=body))
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/optional", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_missing_provider_configuration_fails_closed(auth_transport, monkeypatch):
    requests, _ = auth_transport(
        lambda _request: pytest.fail("Missing configuration reached Auth")
    )
    monkeypatch.delenv("SUPABASE_ANON_KEY")
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/optional", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 503
    assert requests == []


@pytest.mark.asyncio
async def test_wrong_project_token_is_rejected_by_configured_auth(auth_transport):
    token = untrusted_token(uuid4())
    requests, _ = auth_transport(lambda _request: httpx.Response(401))
    async with REAL_ASYNC_CLIENT(
        transport=httpx.ASGITransport(app=auth_app()), base_url="https://app.example"
    ) as client:
        response = await client.get(
            "/optional", headers={"Authorization": f"Bearer {token}"}
        )
    assert response.status_code == 401
    assert len(requests) == 1
    assert str(requests[0].url) == AUTH_URL
