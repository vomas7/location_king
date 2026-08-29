"""
Своя аватарка игрока.

Раньше картинок не было вовсе: аватарка была двумя числами, а узор по ним
рисовал клиент. Игроки попросили загружать своё, и вместе с картинками
появилось всё, от чего тот отказ и уберегал: хранилище, обработка и чужое
изображение, которое видно в таблице лидеров.

Поэтому загруженное не хранится как пришло. Файл открывается, обрезается по
центру в квадрат, приводится к одному размеру и перекодируется в WebP.
Перекодирование здесь не про вес: оно оставляет от файла только пиксели.
Ни EXIF с координатами съёмки, ни постороннего содержимого, спрятанного за
картинкой, в базу не попадает.

Узор при этом никуда не девается: он остаётся у всех, кто ничего не
загружал, и к нему можно вернуться одной кнопкой.
"""

import io
import logging

from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.avatar_image import AvatarImage
from app.models.user import User

logger = logging.getLogger(__name__)

#: Сторона квадрата. Самая крупная аватарка в игре — сорок восемь пикселей на
#: экране, то есть девяносто шесть на плотном; двести пятьдесят шесть дают
#: запас на будущее и всё ещё весят килобайты
SIDE = 256

#: Потолок для загружаемого файла. Восьми мегапикселей хватает любому снимку
#: с телефона, а больше — это уже попытка занять память декодером
MAX_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 8_000_000

#: Что принимаем. Формат определяется по содержимому, а не по имени файла:
#: расширение пишет тот, кто загружает
ALLOWED = {"JPEG", "PNG", "WEBP", "GIF"}

#: Чем отдаём. Один формат на все аватарки: клиенту не нужно гадать, а
#: WebP мельче JPEG при том же качестве
CONTENT_TYPE = "image/webp"


def render(raw: bytes) -> bytes:
    """
    Привести загруженное к аватарке: квадрат SIDE×SIDE в WebP.

    Бросает ValidationError на всём, что не картинка или слишком велико.
    """
    if len(raw) > MAX_BYTES:
        raise ValidationError(f"Файл больше {MAX_BYTES // (1024 * 1024)} МБ")

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ValidationError("Это не картинка или файл повреждён") from e

    if image.format not in ALLOWED:
        raise ValidationError("Подойдёт JPEG, PNG, WebP или GIF")

    width, height = image.size
    if width * height > MAX_PIXELS:
        raise ValidationError("Картинка слишком большая")

    # Прозрачность превращается в белое, а не в чёрное: аватарку одинаково
    # видно и в тёмном оформлении, и в светлом
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        backdrop = Image.new("RGB", image.size, (255, 255, 255))
        backdrop.paste(image, mask=image.split()[-1])
        image = backdrop
    else:
        image = image.convert("RGB")

    # Обрезаем по центру: аватарка везде показана квадратом, и сжать в него
    # прямоугольник значило бы растянуть лицо
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((SIDE, SIDE), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format="WEBP", quality=82, method=4)
    return out.getvalue()


async def save(db: AsyncSession, user: User, raw: bytes) -> User:
    """Сохранить загруженную аватарку и сдвинуть версию."""
    data = render(raw)

    await db.execute(
        insert(AvatarImage)
        .values(user_id=user.id, data=data)
        .on_conflict_do_update(index_elements=[AvatarImage.user_id], set_={"data": data})
    )

    # Версия попадает в адрес картинки: без неё браузер и nginx показывали бы
    # старую ещё сутки
    user.avatar_version += 1
    await db.flush()

    logger.info("Игрок %s загрузил аватарку, %s байт", user.id, len(data))
    return user


async def drop(db: AsyncSession, user: User) -> User:
    """Убрать загруженную аватарку и вернуть игроку узор."""
    await db.execute(delete(AvatarImage).where(AvatarImage.user_id == user.id))

    # Версия обнуляется: по ней клиент и понимает, что картинки больше нет
    user.avatar_version = 0
    await db.flush()

    return user


async def load(db: AsyncSession, user_id: int) -> bytes | None:
    """Картинка игрока, если он её загружал."""
    stmt = select(AvatarImage.data).where(AvatarImage.user_id == user_id)
    return (await db.execute(stmt)).scalar_one_or_none()
