"""Response-level indexing checks without production startup or services."""

from collections.abc import Iterator
from html.parser import HTMLParser
from importlib import import_module
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SummaryHeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_head = False
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "head":
            self.in_head = True
        attributes = dict(attrs)
        if (
            self.in_head
            and tag == "meta"
            and (attributes.get("name") or "").lower() == "robots"
        ):
            self.robots.append(attributes.get("content") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self.in_head = False


@pytest.fixture
def summary_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    # app/__init__.py loads .env on its first import; suppress that explicitly.
    with patch("dotenv.load_dotenv", return_value=False):
        import_module("app")
    from app.routers import summary_router
    from app.services import state_storage_service, telemetry_service

    # Use the real summary router and static-file server, without app.main's
    # logging, environment loading, middleware, or database cleanup lifespan.
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "seo-test-service-key")
    for service in (state_storage_service, telemetry_service):
        monkeypatch.setattr(
            service,
            "load_dotenv",
            Mock(side_effect=AssertionError("Summary shell must not load .env")),
        )
        monkeypatch.setattr(
            service,
            "create_client",
            Mock(side_effect=AssertionError("Summary shell must not use Supabase")),
        )

    monkeypatch.setattr(
        summary_router,
        "SUMMARY_CHAPTER_DIR",
        str(PROJECT_ROOT / "app/static/summary-chapter"),
    )
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app/static"), name="static")
    app.include_router(summary_router.router, prefix="/adventure")
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "path", ["/adventure/summary", "/static/summary-chapter/index.html"]
)
@pytest.mark.parametrize(
    "query", ["", "?state_id=11111111-1111-4111-8111-111111111111"]
)
def test_summary_shell_responses_are_noindex(
    summary_client: TestClient, path: str, query: str
) -> None:
    response = summary_client.get(path + query)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    head = SummaryHeadParser()
    head.feed(response.text)
    directives = {
        directive.strip().lower()
        for content in head.robots
        for directive in content.split(",")
    }
    assert "noindex" in directives
    assert "index" not in directives
    assert '<div id="root"></div>' in response.text
    assert 'type="module" crossorigin src="/adventure/assets/' in response.text
