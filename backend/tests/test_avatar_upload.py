"""
Своя аватарка.

Раньше картинок в игре не было вовсе, и вместе с ними появилось всё, от чего
тот отказ уберегал: хранилище, обработка чужого файла и изображение, которое
видно другим игрокам. Поэтому здесь проверяется не только «загрузилось», но и
то, что в базу попали одни пиксели: без EXIF, без исходного формата и без
того, что могло приехать под видом картинки.
"""

import io

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.avatar_image import AvatarImage
from app.models.user import User
from app.services import avatars


def picture(width: int = 600, height: int = 400, fmt: str = "PNG", **save: object) -> bytes:
    """Картинка нужного размера. Цвет меняется по ширине, чтобы обрезку было видно."""
    image = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            image.putpixel(
                (x, y), (x * 255 // max(width - 1, 1), y * 255 // max(height - 1, 1), 90)
            )

    out = io.BytesIO()
    image.save(out, format=fmt, **save)
    return out.getvalue()


def upload(raw: bytes, name: str = "me.png") -> dict:
    return {"file": (name, raw, "image/png")}


# ─── Обработка ───────────────────────────────────────────────────────────


def test_result_is_a_square_webp():
    out = avatars.render(picture(600, 400))
    image = Image.open(io.BytesIO(out))

    assert image.format == "WEBP"
    assert image.size == (avatars.SIDE, avatars.SIDE)


def test_exif_does_not_survive():
    """
    Снимок с телефона несёт координаты съёмки. Игрок ставит аватарку, а не
    публикует, где он был, — и в базу это попадать не должно.
    """
    original = Image.open(io.BytesIO(picture(400, 400, fmt="JPEG")))
    exif = original.getexif()
    exif[0x9003] = "2026:08:29 20:32:00"

    raw = io.BytesIO()
    original.save(raw, format="JPEG", exif=exif)

    assert Image.open(io.BytesIO(raw.getvalue())).getexif()

    stored = Image.open(io.BytesIO(avatars.render(raw.getvalue())))
    assert not stored.getexif()


def test_transparency_turns_white_not_black():
    """Прозрачный угол не должен превращаться в чёрный на светлой теме."""
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    raw = io.BytesIO()
    image.save(raw, format="PNG")

    stored = Image.open(io.BytesIO(avatars.render(raw.getvalue()))).convert("RGB")
    assert stored.getpixel((10, 10)) == (255, 255, 255)


def test_not_a_picture_is_refused():
    with pytest.raises(ValidationError):
        avatars.render(b"<?php echo 1; ?>" * 100)


def test_a_file_too_big_is_refused():
    with pytest.raises(ValidationError):
        avatars.render(b"\x00" * (avatars.MAX_BYTES + 1))


# ─── Через API ───────────────────────────────────────────────────────────


async def test_uploaded_avatar_appears_in_the_profile(
    client: AsyncClient, auth_headers: dict, registered_user: User
):
    before = (await client.get("/api/auth/me", headers=auth_headers)).json()
    assert before["avatar"]["image_url"] is None

    response = await client.put(
        "/api/auth/me/avatar", files=upload(picture()), headers=auth_headers
    )

    assert response.status_code == 200, response.text
    url = response.json()["avatar"]["image_url"]
    assert url == f"/api/avatars/{registered_user.id}?v=1"


async def test_uploaded_avatar_is_served_as_webp(
    client: AsyncClient, auth_headers: dict, registered_user: User
):
    await client.put("/api/auth/me/avatar", files=upload(picture()), headers=auth_headers)

    response = await client.get(f"/api/avatars/{registered_user.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert "max-age" in response.headers["Cache-Control"]
    assert Image.open(io.BytesIO(response.content)).size == (avatars.SIDE, avatars.SIDE)


async def test_replacing_the_avatar_changes_the_address(
    client: AsyncClient, auth_headers: dict, registered_user: User
):
    """Иначе браузер неделю показывал бы старую картинку из кэша."""
    first = await client.put("/api/auth/me/avatar", files=upload(picture()), headers=auth_headers)
    second = await client.put(
        "/api/auth/me/avatar", files=upload(picture(300, 300)), headers=auth_headers
    )

    assert first.json()["avatar"]["image_url"] != second.json()["avatar"]["image_url"]


async def test_removing_the_avatar_brings_the_pattern_back(
    client: AsyncClient, auth_headers: dict, registered_user: User, db: AsyncSession
):
    await client.put("/api/auth/me/avatar", files=upload(picture()), headers=auth_headers)

    response = await client.delete("/api/auth/me/avatar", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["avatar"]["image_url"] is None
    # Узор на месте: к нему и возвращаемся
    assert body["avatar"]["shape"] is not None

    stored = await db.execute(select(AvatarImage).where(AvatarImage.user_id == registered_user.id))
    assert stored.scalar_one_or_none() is None


async def test_a_broken_file_is_refused_by_the_api(client: AsyncClient, auth_headers: dict):
    response = await client.put(
        "/api/auth/me/avatar",
        files={"file": ("me.png", b"not a picture at all", "image/png")},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "картинка" in response.json()["detail"].lower()


async def test_avatars_need_authorization(client: AsyncClient, registered_user: User):
    assert (await client.get(f"/api/avatars/{registered_user.id}")).status_code == 401
    assert (await client.put("/api/auth/me/avatar", files=upload(picture()))).status_code == 401


async def test_a_player_without_a_picture_has_none_to_serve(
    client: AsyncClient, auth_headers: dict, registered_user: User
):
    response = await client.get(f"/api/avatars/{registered_user.id}", headers=auth_headers)

    assert response.status_code == 404


async def test_deleting_the_account_takes_the_picture_with_it(
    client: AsyncClient, auth_headers: dict, registered_user: User, db: AsyncSession
):
    """Картинка — такие же данные игрока, как и всё остальное."""
    await client.put("/api/auth/me/avatar", files=upload(picture()), headers=auth_headers)
    user_id = registered_user.id

    response = await client.post(
        "/api/auth/me/delete",
        json={"password": "correct horse battery"},
        headers=auth_headers,
    )
    assert response.status_code == 204, response.text

    stored = await db.execute(select(AvatarImage).where(AvatarImage.user_id == user_id))
    assert stored.scalar_one_or_none() is None
