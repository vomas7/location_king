"""Базовые тесты Location King backend."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Тестовый клиент FastAPI."""
    return TestClient(app)


def test_health_endpoint(client):
    """Health-эндпоинт отвечает и сообщает имя сервиса."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "location-king-backend"
    assert "version" in data
