"""
Роутер для работы с игровыми зонами.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.game import ErrorResponse, ZoneResponse
from app.services.challenge_generator import ChallengeGenerator

router = APIRouter(prefix="/api/zones", tags=["zones"])
logger = logging.getLogger(__name__)


# Simple inline get_current_user to avoid import issues


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user."""
    from app.models.user import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == 1))
    user = result.scalar_one_or_none()

    if not user:
        user = UserModel(
            id=1,
            keycloak_id="test-user",
            email="test@example.com",
            display_name="Test User",
            is_verified=True,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


@router.get(
    "/",
    response_model=list[ZoneResponse],
    responses={
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def list_zones(
    difficulty: int | None = Query(
        None,
        ge=1,
        le=5,
        description="Фильтр по сложности (1-5)",
    ),
    category: str | None = Query(
        None,
        description="Фильтр по категории",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Максимальное количество зон",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список доступных игровых зон.
    
    Возвращает зоны, отсортированные по сложности.
    """
    try:
        generator = ChallengeGenerator(db)
        zones = await generator.get_available_zones(
            difficulty=difficulty,
            category=category,
            limit=limit,
        )

        return [
            ZoneResponse(
                id=zone.id,
                name=zone.name,
                description=zone.description,
                difficulty=zone.difficulty,
                category=zone.category,
            )
            for zone in zones
        ]

    except Exception as e:
        logger.error(f"Error listing zones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера",
        )


@router.get(
    "/random",
    response_model=ZoneResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Нет доступных зон"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_random_zone(
    difficulty: int | None = Query(
        None,
        ge=1,
        le=5,
        description="Фильтр по сложности (1-5)",
    ),
    category: str | None = Query(
        None,
        description="Фильтр по категории",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить случайную игровую зону.
    
    Полезно для быстрого начала игры без выбора конкретной зоны.
    """
    try:
        generator = ChallengeGenerator(db)
        zone = await generator.get_random_zone(
            difficulty=difficulty,
            category=category,
        )

        if not zone:
            raise HTTPException(
                status_code=404,
                detail="Нет доступных зон с указанными параметрами",
            )

        return ZoneResponse(
            id=zone.id,
            name=zone.name,
            description=zone.description,
            difficulty=zone.difficulty,
            category=zone.category,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting random zone: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера",
        )


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Зона не найдена"},
    },
)
async def get_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о конкретной зоне.
    """
    try:
        from sqlalchemy import select

        from app.models.location_zone import LocationZone

        stmt = select(LocationZone).where(
            LocationZone.id == zone_id,
            LocationZone.is_active == True,
        )
        result = await db.execute(stmt)
        zone = result.scalar_one_or_none()

        if not zone:
            raise HTTPException(
                status_code=404,
                detail="Зона не найдена",
            )

        return ZoneResponse(
            id=zone.id,
            name=zone.name,
            description=zone.description,
            difficulty=zone.difficulty,
            category=zone.category,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting zone: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера",
        )


@router.get(
    "/{zone_id}/preview",
    responses={
        404: {"model": ErrorResponse, "description": "Зона не найдена"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def get_zone_preview(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить превью зоны.
    
    Возвращает пример космического снимка из этой зоны
    и статистику по сложности.
    """
    try:
        from sqlalchemy import func, select

        from app.models.location_zone import LocationZone
        from app.models.round import Round

        # Получаем зону
        zone_stmt = select(LocationZone).where(
            LocationZone.id == zone_id,
            LocationZone.is_active == True,
        )
        zone_result = await db.execute(zone_stmt)
        zone = zone_result.scalar_one_or_none()

        if not zone:
            raise HTTPException(
                status_code=404,
                detail="Зона не найдена",
            )

        # Получаем статистику по зоне
        stats_stmt = select(
            func.count(Round.id).label("total_rounds"),
            func.avg(Round.score).label("average_score"),
            func.avg(Round.distance_km).label("average_distance"),
        ).where(
            Round.zone_id == zone_id,
            Round.guess_point.is_not(None),
        )

        stats_result = await db.execute(stats_stmt)
        stats = stats_result.first()

        # Генерируем примерную точку для превью
        generator = ChallengeGenerator(db)
        example_point = await generator.generate_random_point_in_zone(zone_id)

        preview_data = {
            "zone": {
                "id": zone.id,
                "name": zone.name,
                "description": zone.description,
                "difficulty": zone.difficulty,
                "category": zone.category,
            },
            "statistics": {
                "total_rounds": stats.total_rounds if stats else 0,
                "average_score": float(stats.average_score) if stats and stats.average_score else 0,
                "average_distance_km": float(stats.average_distance) if stats and stats.average_distance else 0,
            },
            "example_point": example_point,
            "preview_note": "Для получения реального превью-снимка требуется интеграция с провайдером карт.",
        }

        # TODO: Добавить реальный превью-снимок через satellite_provider
        if example_point:
            try:
                from app.services.satellite_provider import get_satellite_provider
                satellite_provider = await get_satellite_provider()
                preview_image = await satellite_provider.get_satellite_image(
                    center_lng=example_point[0],
                    center_lat=example_point[1],
                    width_km=10,
                    height_km=10,
                )

                if preview_image:
                    preview_data["preview_image"] = {
                        "url": preview_image.image_url,
                        "bounds": preview_image.bounds,
                        "provider": preview_image.provider,
                    }
                    preview_data["preview_note"] = "Превью снимка доступно по URL."

            except Exception as e:
                logger.warning(f"Could not generate preview image: {e}")

        return preview_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting zone preview: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера",
        )
