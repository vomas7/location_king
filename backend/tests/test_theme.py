"""
Оформление интерфейса.

Тема хранится у игрока, а не в браузере: смысл проверок в том, что выбор
переживает новый вход, а не в том, как он выглядит.
"""

from httpx import AsyncClient

from app.models.enums import Theme
from app.models.user import User


async def test_new_player_gets_dark_theme(client: AsyncClient, auth_headers: dict):
    """Тёмная была у всех до появления выбора — сюрпризов быть не должно."""
    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["theme"] == Theme.DARK


async def test_theme_is_saved(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/auth/me/theme",
        json={"theme": "light"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["theme"] == "light"

    again = await client.get("/api/auth/me", headers=auth_headers)
    assert again.json()["theme"] == "light"


async def test_theme_survives_new_login(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
):
    """Ради этого тема и лежит на сервере, а не в хранилище браузера."""
    await client.put("/api/auth/me/theme", json={"theme": "system"}, headers=auth_headers)

    response = await client.post(
        "/api/auth/login",
        json={"email": registered_user.email, "password": "correct horse battery"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["theme"] == "system"


async def test_unknown_theme_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/auth/me/theme",
        json={"theme": "неоновая"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_theme_needs_authorization(client: AsyncClient):
    response = await client.put("/api/auth/me/theme", json={"theme": "light"})

    assert response.status_code == 401
