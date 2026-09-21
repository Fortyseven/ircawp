"""Backend-load failures must surface as JSON errors (500 + detail), not
plain-text 500s from an unhandled exception.

The frontend's api.js parses the error body for `detail`; a non-JSON body
breaks that contract.
"""

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_backend_load_failure_returns_json_500(monkeypatch):
    def boom(backend_id):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(main_module, "get_backend", boom)

    response = client.post(
        "/images/generations", json={"prompt": "a test", "model": "qwenimage21"}
    )

    assert response.status_code == 500
    data = response.json()
    assert "CUDA out of memory" in data["detail"]


def test_backend_load_failure_on_edits_returns_json_500(monkeypatch):
    def boom(backend_id):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(main_module, "get_backend", boom)

    response = client.post(
        "/images/edits",
        json={
            "prompt": "a test",
            "images": [{"image_url": "data:image/png;base64,aGk="}],
        },
    )

    assert response.status_code == 500
    data = response.json()
    assert "CUDA out of memory" in data["detail"]
