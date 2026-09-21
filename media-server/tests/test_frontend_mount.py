"""Integration tests for serving the built Svelte frontend from frontend/dist/.

The FastAPI app should mount `frontend/dist/` (resolved relative to the app
package, i.e. media-server/frontend/dist) at `/` as a catch-all static mount
AFTER all API routes, so API routes take precedence. When the dist directory
does not exist, the app must still start and API routes must work, with
`GET /` returning 404.

The mount decision happens at import time, so these tests use
`importlib.reload(app.main)` after creating/removing the dist directory and
build a fresh TestClient from the reloaded module's app.
"""

import importlib
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main

# media-server/frontend/dist (app/main.py -> app/ -> media-server/)
DIST_DIR = Path(app.main.__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_DIR = DIST_DIR.parent
MARKER = "<!-- frontend-mount-test -->"


def _reload_client() -> TestClient:
    """Reload app.main (re-runs the import-time mount check) and return a fresh client."""
    importlib.reload(app.main)
    return TestClient(app.main.app)


@pytest.fixture(scope="module")
def client_with_dist():
    """App reloaded with frontend/dist/index.html present (recognizable marker).

    A pre-existing dist (e.g. a real build) is preserved: the original
    index.html is backed up and restored on teardown.
    """
    created = not DIST_DIR.exists()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    index = DIST_DIR / "index.html"
    original = index.read_text() if index.exists() else None
    index.write_text(f"<html><body>{MARKER}</body></html>")

    client = _reload_client()
    yield client

    # Teardown: restore the original index.html (or remove what we created),
    # then reload so module state matches the filesystem again.
    if original is not None:
        index.write_text(original)
    else:
        index.unlink(missing_ok=True)
        if created and DIST_DIR.is_dir() and not any(DIST_DIR.iterdir()):
            DIST_DIR.rmdir()
        if FRONTEND_DIR.is_dir() and not any(FRONTEND_DIR.iterdir()):
            FRONTEND_DIR.rmdir()
    importlib.reload(app.main)


@pytest.fixture(scope="module")
def client_without_dist():
    """App reloaded with frontend/dist absent.

    A pre-existing dist (e.g. a real build) is moved aside and restored on
    teardown — never deleted.
    """
    backup = DIST_DIR.with_name("dist.test-backup")
    had_dist = DIST_DIR.exists()
    if had_dist:
        shutil.move(str(DIST_DIR), str(backup))

    client = _reload_client()
    yield client

    if had_dist:
        shutil.move(str(backup), str(DIST_DIR))
    importlib.reload(app.main)


def test_root_serves_frontend_index_when_dist_present(client_with_dist):
    response = client_with_dist.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert MARKER in response.text


def test_api_routes_take_precedence_over_static_mount(client_with_dist):
    response = client_with_dist.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_returns_404_when_dist_absent(client_without_dist):
    response = client_without_dist.get("/")
    assert response.status_code == 404


def test_health_still_works_when_dist_absent(client_without_dist):
    response = client_without_dist.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
