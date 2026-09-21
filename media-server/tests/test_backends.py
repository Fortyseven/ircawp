"""Integration tests for GET /backends metadata endpoint.

Verifies the endpoint returns the configured default backend and the
sorted list of configured backend IDs, without instantiating any backend.
"""

from fastapi.testclient import TestClient

from app.main import CONFIG, DEFAULT_BACKEND, app

client = TestClient(app)


def test_backends_endpoint_returns_200():
    response = client.get("/backends")
    assert response.status_code == 200


def test_backends_endpoint_returns_default_backend():
    response = client.get("/backends")
    assert response.status_code == 200
    data = response.json()
    assert data["default"] == DEFAULT_BACKEND


def test_backends_endpoint_returns_sorted_configured_backends():
    response = client.get("/backends")
    assert response.status_code == 200
    data = response.json()
    expected = sorted((CONFIG.get("backends") or {}).keys())
    assert data["backends"] == expected


def test_backends_endpoint_response_shape():
    response = client.get("/backends")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"default", "backends"}
    assert isinstance(data["default"], str)
    assert isinstance(data["backends"], list)
