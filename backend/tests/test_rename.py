"""Смена публичного имени игрока."""

import pytest
from httpx import AsyncClient

from app.exceptions import ValidationError
from app.services.auth import MAX_DISPLAY_NAME, clean_display_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Гео   Король  ", "Гео Король"),
        # Неразрывный пробел и перевод строки — обычные пробелы: рисовать ими
        # разъезжающуюся колонку в таблице лидеров не выйдет
        ("Гео\u00a0Король", "Гео Король"),
        ("Гео\nКороль", "Гео Король"),
    ],
)
def test_whitespace_is_normalised(raw: str, expected: str):
    assert clean_display_name(raw) == expected


def test_name_is_trimmed():
    assert clean_display_name("  Кот  ") == "Кот"


@pytest.mark.parametrize(
    "name",
    [
        "К",
        "   ",
        "К" * (MAX_DISPLAY_NAME + 1),
        "player@example.com",
        "Гео\u200bкороль",  # невидимый разделитель
        "Гео\u202eкороль",  # смена направления письма
        "<b>Гео</b>",
        "Гео;DROP TABLE users",
    ],
)
def test_bad_names_are_rejected(name: str):
    with pytest.raises(ValidationError):
        clean_display_name(name)


@pytest.mark.parametrize(
    "name", ["Кот", "Гео Король", "player_1", "Анна-Мария", "О'Брайен", "陳大文"]
)
def test_good_names_pass(name: str):
    assert clean_display_name(name) == name


async def test_rename_changes_the_profile(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/auth/me", json={"display_name": "  Гео Король  "}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Гео Король"

    profile = await client.get("/api/auth/me", headers=auth_headers)
    assert profile.json()["display_name"] == "Гео Король"


async def test_rename_rejects_a_bad_name(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/auth/me", json={"display_name": "я@почта.рф"}, headers=auth_headers
    )

    assert response.status_code == 400
    assert "почт" in response.json()["detail"].lower()


async def test_rename_needs_a_token(client: AsyncClient):
    response = await client.patch("/api/auth/me", json={"display_name": "Кто-то"})

    assert response.status_code == 401


async def test_rename_does_not_leak_other_players(client: AsyncClient, auth_headers: dict):
    """Ответ — тот же профиль, что и у /me: чужих данных в нём быть не должно."""
    renamed = await client.patch(
        "/api/auth/me", json={"display_name": "Наблюдатель"}, headers=auth_headers
    )
    profile = await client.get("/api/auth/me", headers=auth_headers)

    assert set(renamed.json()) == set(profile.json())
