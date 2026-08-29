"""HTTP-слой аватарок: загрузка своей картинки и отдача её другим."""

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.schemas.auth import UserProfile
from app.services import avatars as avatars_service
from app.services.rate_limit import Limit

router = APIRouter(tags=["avatars"])

#: Аватарка меняется редко, а показывается в каждой строке таблицы. Адрес
#: несёт версию и меняется при замене, поэтому кэшировать можно надолго
CACHE_CONTROL = "public, max-age=604800, immutable"


@router.put(
    "/api/auth/me/avatar",
    response_model=UserProfile,
    dependencies=[Depends(limit_by_user(Limit.AVATAR))],
)
async def upload_avatar(
    file: UploadFile = File(description="Картинка: JPEG, PNG, WebP или GIF"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """
    Загрузить свою аватарку.

    Файл не сохраняется как пришёл: он перекодируется в квадратный WebP, и в
    базу попадают только пиксели.
    """
    # Читаем с потолком, а не целиком: nginx ограничивает тело запроса, но
    # бэкенд не должен полагаться на то, что перед ним кто-то стоит. Лишний
    # байт сверх предела — уже отказ, и тянуть остальное в память незачем
    raw = await file.read(avatars_service.MAX_BYTES + 1)
    if not raw:
        raise ValidationError("Файл пустой")

    updated = await avatars_service.save(db, user, raw)
    return UserProfile.model_validate(updated)


@router.delete(
    "/api/auth/me/avatar",
    response_model=UserProfile,
    dependencies=[Depends(limit_by_user(Limit.AVATAR))],
)
async def drop_avatar(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Убрать загруженную аватарку и вернуться к узору."""
    updated = await avatars_service.drop(db, user)
    return UserProfile.model_validate(updated)


@router.get(
    "/api/avatars/{user_id}",
    response_class=Response,
    responses={200: {"content": {avatars_service.CONTENT_TYPE: {}}}},
)
async def get_avatar(
    user_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Аватарка игрока картинкой.

    Авторизация нужна, как и везде: аватарки видны игрокам, а не поисковикам.
    Версия в адресе игнорируется — она нужна только затем, чтобы адрес
    поменялся и кэш не отдал прежнюю картинку.
    """
    data = await avatars_service.load(db, user_id)
    if data is None:
        raise NotFoundError("У этого игрока нет загруженной аватарки")

    return Response(
        content=data,
        media_type=avatars_service.CONTENT_TYPE,
        headers={"Cache-Control": CACHE_CONTROL},
    )
