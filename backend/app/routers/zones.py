"""HTTP-слой игровых зон."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.enums import Continent, CountryGroup, Difficulty, ZoneCollection
from app.schemas.game import ZoneView
from app.services import views
from app.services import zones as zones_service

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("", response_model=list[ZoneView])
async def list_zones(
    difficulty: Difficulty | None = None,
    category: str | None = None,
    continent: Continent | None = None,
    country_group: CountryGroup | None = None,
    collection: ZoneCollection | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ZoneView]:
    """Список активных зон."""
    zones = await zones_service.list_zones(
        db, difficulty, category, continent, country_group, collection, limit
    )
    return [views.zone_view(zone) for zone in zones]


@router.get("/{zone_id}", response_model=ZoneView)
async def get_zone(zone_id: int, db: AsyncSession = Depends(get_db)) -> ZoneView:
    """Одна зона по id."""
    return views.zone_view(await zones_service.get_zone(db, zone_id))
