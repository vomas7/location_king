"""Тесты аутентификации."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.auth import create_token, hash_password, verify_password


async def test_register_returns_profile_and_tokens(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "long enough password"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["is_guest"] is False
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["expires_in"] == settings.access_token_ttl_minutes * 60


async def test_register_never_returns_password_hash(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "secret@example.com", "password": "long enough password"},
    )

    assert "password" not in response.text
    assert "hash" not in response.text


async def test_register_rejects_duplicate_email(client: AsyncClient, registered_user: User):
    response = await client.post(
        "/api/auth/register",
        json={"email": "PLAYER@example.com", "password": "correct horse battery"},
    )

    assert response.status_code == 409


async def test_register_rejects_short_password(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "1234567"},
    )

    assert response.status_code == 422


async def test_register_rejects_malformed_email(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "long enough password"},
    )

    assert response.status_code == 422


async def test_login_succeeds_with_correct_password(client: AsyncClient, registered_user: User):
    response = await client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "correct horse battery"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == registered_user.id


async def test_login_is_case_insensitive_for_email(client: AsyncClient, registered_user: User):
    response = await client.post(
        "/api/auth/login",
        json={"email": "  PlaYer@Example.COM ", "password": "correct horse battery"},
    )

    assert response.status_code == 200


async def test_login_rejects_wrong_password(client: AsyncClient, registered_user: User):
    response = await client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "wrong password here"},
    )

    assert response.status_code == 401


async def test_login_rejects_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "any password here"},
    )

    assert response.status_code == 401


async def test_guest_can_play_without_registration(client: AsyncClient):
    response = await client.post("/api/auth/guest")

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["is_guest"] is True
    assert body["user"]["email"] is None


async def test_me_requires_token(client: AsyncClient):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_returns_current_user(client: AsyncClient, auth_headers: dict, guest: dict):
    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == guest["user"]["id"]


async def test_expired_access_token_is_rejected(client: AsyncClient, registered_user: User):
    expired = jwt.encode(
        {
            "sub": str(registered_user.id),
            "type": "access",
            "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


async def test_token_signed_with_another_secret_is_rejected(
    client: AsyncClient,
    registered_user: User,
):
    forged = jwt.encode(
        {
            "sub": str(registered_user.id),
            "type": "access",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        "not-our-secret",
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


async def test_refresh_token_is_not_accepted_as_access_token(
    client: AsyncClient,
    registered_user: User,
):
    refresh = create_token(registered_user.id, "refresh")

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


async def test_refresh_returns_new_pair(client: AsyncClient, guest: dict):
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": guest["tokens"]["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient, guest: dict):
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": guest["tokens"]["access_token"]},
    )

    assert response.status_code == 401


async def test_refresh_rejects_garbage(client: AsyncClient):
    response = await client.post("/api/auth/refresh", json={"refresh_token": "not.a.token"})
    assert response.status_code == 401


async def test_disabled_user_cannot_authenticate(
    client: AsyncClient,
    db: AsyncSession,
    registered_user: User,
):
    registered_user.is_active = False
    await db.flush()

    token = create_token(registered_user.id, "access")
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.parametrize("password", ["short one", "a very long passphrase with spaces"])
def test_password_hash_roundtrip(password: str):
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password(password + "x", hashed) is False


def test_verify_password_rejects_broken_hash():
    assert verify_password("anything", "не хеш вовсе") is False
