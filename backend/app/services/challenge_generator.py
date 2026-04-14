"""
Сервис для генерации игровых вызовов (раундов).
"""
import logging
import random
from typing import Optional, Tuple

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services.satellite_provider import get_satellite_provider
from app.utils.geometry_utils import LocationZoneUtils, CoordinateUtils

logger = logging.getLogger(__name__)


class ChallengeGenerator:
    """Генератор игровых вызовов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def generate_random_point_in_zone(self, zone_id: int) -> Optional[Tuple[float, float]]:
        """
        Сгенерировать случайную точку внутри указанной зоны.
        
        Args:
            zone_id: ID зоны LocationZone
            
        Returns:
            Кортеж (longitude, latitude) или None если зона не найдена
        """
        return await LocationZoneUtils.get_random_point_in_zone(self.session, zone_id)
    
    async def generate_round(
        self,
        session_id: str,
        zone_id: int,
        view_extent_km: int = 5,
    ) -> Optional[Round]:
        """
        Сгенерировать новый раунд для игровой сессии.
        
        Args:
            session_id: ID игровой сессии
            zone_id: ID зоны для генерации точки
            view_extent_km: Размер области снимка в км
            
        Returns:
            Объект Round или None в случае ошибки
        """
        try:
            # 1. Генерируем случайную точку в зоне
            target_point = await self.generate_random_point_in_zone(zone_id)
            if not target_point:
                return None
            
            lng, lat = target_point
            
            # 2. Получаем космический снимок для этой области
            satellite_provider = await get_satellite_provider()
            satellite_image = await satellite_provider.get_satellite_image(
                center_lng=lng,
                center_lat=lat,
                width_km=view_extent_km,
                height_km=view_extent_km,
            )
            
            if not satellite_image:
                logger.error(f"Failed to get satellite image for point ({lng}, {lat})")
                return None
            
            # 3. Создаём объект раунда
            round_obj = Round(
                session_id=session_id,
                zone_id=zone_id,
                target_point=WKTElement(f"POINT({lng} {lat})", srid=4326),
                view_extent_km=view_extent_km,
            )
            
            # 4. Сохраняем в БД
            self.session.add(round_obj)
            await self.session.flush()
            
            logger.info(f"Generated round {round_obj.id} for session {session_id}")
            return round_obj
            
        except Exception as e:
            logger.error(f"Error generating round: {e}")
            await self.session.rollback()
            return None
    
    async def get_available_zones(
        self,
        difficulty: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[LocationZone]:
        """
        Получить список доступных зон для игры.
        
        Args:
            difficulty: Фильтр по сложности (1-5)
            category: Фильтр по категории
            limit: Максимальное количество зон
            
        Returns:
            Список объектов LocationZone
        """
        try:
            stmt = select(LocationZone).where(LocationZone.is_active == True)
            
            if difficulty is not None:
                stmt = stmt.where(LocationZone.difficulty == difficulty)
            
            if category is not None:
                stmt = stmt.where(LocationZone.category == category)
            
            stmt = stmt.order_by(LocationZone.difficulty).limit(limit)
            
            result = await self.session.execute(stmt)
            zones = result.scalars().all()
            
            return list(zones)
            
        except Exception as e:
            logger.error(f"Error getting available zones: {e}")
            return []
    
    async def get_random_zone(
        self,
        difficulty: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Optional[LocationZone]:
        """
        Получить случайную зону для игры.
        
        Args:
            difficulty: Фильтр по сложности (1-5)
            category: Фильтр по категории
            
        Returns:
            Объект LocationZone или None
        """
        try:
            zones = await self.get_available_zones(difficulty, category, limit=50)
            if not zones:
                return None
            
            return random.choice(zones)
            
        except Exception as e:
            logger.error(f"Error getting random zone: {e}")
            return None


# Утилитарные функции для работы с геометрией
class GeometryUtils:
    """Утилиты для работы с геоданными"""
    
    @staticmethod
    def calculate_distance(
        point1_lng: float,
        point1_lat: float,
        point2_lng: float,
        point2_lat: float,
    ) -> float:
        """
        Рассчитать расстояние между двумя точками в километрах.
        Использует формулу гаверсинусов.
        
        Args:
            point1_lng, point1_lat: Координаты первой точки
            point2_lng, point2_lat: Координаты второй точки
            
        Returns:
            Расстояние в километрах
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Радиус Земли в километрах
        R = 6371.0
        
        # Конвертируем градусы в радианы
        lat1 = radians(point1_lat)
        lon1 = radians(point1_lng)
        lat2 = radians(point2_lat)
        lon2 = radians(point2_lng)
        
        # Разницы координат
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        # Формула гаверсинусов
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
    
    @staticmethod
    def calculate_score(distance_km: float, max_distance_km: int = 100) -> int:
        """
        Рассчитать очки на основе расстояния.
        
        Формула: score = max(0, 5000 - (distance_km / max_distance_km) * 5000)
        Максимальный счёт (5000) за точное попадание (0 км)
        Минимальный счёт (0) за расстояние > max_distance_km
        
        Args:
            distance_km: Расстояние в километрах
            max_distance_km: Максимальное расстояние для получения очков
            
        Returns:
            Количество очков (0-5000)
        """
        if distance_km >= max_distance_km:
            return 0
        
        # Линейная формула
        score = int(5000 * (1 - distance_km / max_distance_km))
        
        # Округляем до ближайших 10
        score = (score // 10) * 10
        
        return max(0, min(5000, score))