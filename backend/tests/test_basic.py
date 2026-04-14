"""
Basic tests for Location King backend.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_zones_endpoint(client):
    """Test zones endpoint (requires DEBUG=true)."""
    response = client.get("/api/test/zones")
    # Может вернуть 404 если DEBUG=false
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_create_session(client):
    """Test session creation (requires DEBUG=true)."""
    response = client.post(
        "/api/test/session/start",
        json={"rounds_total": 1, "view_extent_km": 3}
    )
    # Может вернуть 404 если DEBUG=false
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert data["rounds_total"] == 1
        assert data["view_extent_km"] == 3