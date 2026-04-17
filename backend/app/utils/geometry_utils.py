"""
Утилиты для работы с геоданными и LocationZone.
"""

import logging
import random
from math import asin, atan2, cos, degrees, radians, sin

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone

logger = logging.getLogger(__name__)


class LocationZoneUtils:
    """Утилиты для работы с игровыми зонами"""

    @staticmethod
    async def get_random_point_in_zone(
        session: AsyncSession,
        zone_id: int,
        max_attempts: int = 10,
    ) -> tuple[float, float] | None:
        """
        Получить случайную точку внутри указанной зоны.

        Использует PostGIS функцию ST_GeneratePoints для генерации случайной точки
        внутри полигона зоны.

        Args:
            session: Асинхронная сессия БД
            zone_id: ID зоны LocationZone
            max_attempts: Максимальное количество попыток генерации

        Returns:
            Кортеж (longitude, latitude) или None если зона не найдена
        """
        try:
            # Получаем зону
            zone_stmt = select(LocationZone).where(
                LocationZone.id == zone_id,
                LocationZone.is_active == True,
            )
            zone_result = await session.execute(zone_stmt)
            zone = zone_result.scalar_one_or_none()

            if not zone:
                logger.error(f"Zone {zone_id} not found or inactive")
                return None

            # Генерируем случайную точку внутри полигона зоны
            # Используем PostGIS функцию ST_GeneratePoints (возвращает MULTIPOINT)
            for attempt in range(max_attempts):
                # ST_GeneratePoints возвращает MULTIPOINT, извлекаем первую точку с ST_PointN
                point_stmt = select(
                    func.ST_X(func.ST_PointN(func.ST_GeneratePoints(zone.polygon, 1), 1)),
                    func.ST_Y(func.ST_PointN(func.ST_GeneratePoints(zone.polygon, 1), 1)),
                )
                point_result = await session.execute(point_stmt)
                point = point_result.first()

                if point and point[0] is not None and point[1] is not None:
                    lng, lat = point
                    return float(lng), float(lat)

                logger.warning(f"Attempt {attempt + 1} failed to generate point in zone {zone_id}")

                # Альтернативный метод: используем ST_GeneratePoints с другим подходом
                if attempt == max_attempts // 2:
                    try:
                        # Попробуем другой метод: генерируем точку в bounding box
                        bbox_stmt = select(
                            func.ST_X(func.ST_Centroid(zone.polygon)),
                            func.ST_Y(func.ST_Centroid(zone.polygon)),
                        )
                        bbox_result = await session.execute(bbox_stmt)
                        centroid = bbox_result.first()
                        if centroid and centroid[0] is not None and centroid[1] is not None:
                            # Возвращаем центр зоны как fallback
                            return float(centroid[0]), float(centroid[1])
                    except Exception as e:
                        logger.warning(f"Centroid fallback failed: {e}")

            logger.error(
                f"Failed to generate point in zone {zone_id} after {max_attempts} attempts"
            )
            return None

        except Exception as e:
            logger.error(f"Error generating random point: {e}")
            return None

    @staticmethod
    async def get_zone_area_km2(
        session: AsyncSession,
        zone_id: int,
    ) -> float | None:
        """
        Получить площадь зоны в квадратных километрах.

        Args:
            session: Асинхронная сессия БД
            zone_id: ID зоны LocationZone

        Returns:
            Площадь в км² или None
        """
        try:
            # Используем PostGIS функцию ST_Area с преобразованием в проекцию для метров
            area_stmt = select(
                func.ST_Area(
                    func.ST_Transform(
                        LocationZone.polygon, 3857
                    ),  # Web Mercator для расчёта в метрах
                )
                / 1000000,  # Конвертируем м² в км²
            ).where(
                LocationZone.id == zone_id,
            )

            area_result = await session.execute(area_stmt)
            area = area_result.scalar_one_or_none()

            return float(area) if area else None

        except Exception as e:
            logger.error(f"Error calculating zone area: {e}")
            return None

    @staticmethod
    async def is_point_in_zone(
        session: AsyncSession,
        zone_id: int,
        longitude: float,
        latitude: float,
    ) -> bool:
        """
        Проверить, находится ли точка внутри зоны.

        Args:
            session: Асинхронная сессия БД
            zone_id: ID зоны LocationZone
            longitude: Долгота точки
            latitude: Широта точки

        Returns:
            True если точка внутри зоны, иначе False
        """
        try:
            # Создаём WKT точку
            point_wkt = f"POINT({longitude} {latitude})"

            # Используем PostGIS функцию ST_Contains
            contains_stmt = select(
                func.ST_Contains(
                    LocationZone.polygon,
                    func.ST_GeomFromText(point_wkt, 4326),
                ),
            ).where(
                LocationZone.id == zone_id,
            )

            contains_result = await session.execute(contains_stmt)
            contains = contains_result.scalar_one_or_none()

            return bool(contains) if contains is not None else False

        except Exception as e:
            logger.error(f"Error checking point in zone: {e}")
            return False

    @staticmethod
    async def get_zone_bounds(
        session: AsyncSession,
        zone_id: int,
    ) -> tuple[float, float, float, float] | None:
        """
        Получить границы (bounding box) зоны.

        Args:
            session: Асинхронная сессия БД
            zone_id: ID зоны LocationZone

        Returns:
            Кортеж (min_lng, min_lat, max_lng, max_lat) или None
        """
        try:
            # Используем PostGIS функцию ST_Extent
            bounds_stmt = select(
                func.ST_XMin(func.ST_Extent(LocationZone.polygon)),
                func.ST_YMin(func.ST_Extent(LocationZone.polygon)),
                func.ST_XMax(func.St_Extent(LocationZone.polygon)),
                func.ST_YMax(func.ST_Extent(LocationZone.polygon)),
            ).where(
                LocationZone.id == zone_id,
            )

            bounds_result = await session.execute(bounds_stmt)
            bounds = bounds_result.first()

            if bounds:
                return (
                    float(bounds[0]),  # min_lng
                    float(bounds[1]),  # min_lat
                    float(bounds[2]),  # max_lng
                    float(bounds[3]),  # max_lat
                )
            return None

        except Exception as e:
            logger.error(f"Error getting zone bounds: {e}")
            return None

    @staticmethod
    async def get_zones_containing_point(
        session: AsyncSession,
        longitude: float,
        latitude: float,
        limit: int = 10,
    ) -> list[LocationZone]:
        """
        Получить зоны, содержащие указанную точку.

        Args:
            session: Асинхронная сессия БД
            longitude: Долгота точки
            latitude: Широта точки
            limit: Максимальное количество зон

        Returns:
            Список зон LocationZone
        """
        try:
            point_wkt = f"POINT({longitude} {latitude})"

            zones_stmt = (
                select(LocationZone)
                .where(
                    func.ST_Contains(
                        LocationZone.polygon,
                        func.ST_GeomFromText(point_wkt, 4326),
                    ),
                    LocationZone.is_active == True,
                )
                .limit(limit)
            )

            zones_result = await session.execute(zones_stmt)
            zones = zones_result.scalars().all()

            return list(zones)

        except Exception as e:
            logger.error(f"Error getting zones containing point: {e}")
            return []

    @staticmethod
    async def create_zone_from_bbox(
        session: AsyncSession,
        name: str,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        difficulty: int = 1,
        category: str | None = None,
        description: str | None = None,
    ) -> LocationZone | None:
        """
        Создать новую зону из bounding box.

        Args:
            session: Асинхронная сессия БД
            name: Название зоны
            min_lng: Минимальная долгота
            min_lat: Минимальная широта
            max_lng: Максимальная долгота
            max_lat: Максимальная широта
            difficulty: Сложность (1-5)
            category: Категория зоны
            description: Описание зоны

        Returns:
            Созданная зона или None в случае ошибки
        """
        try:
            # Создаём полигон из bounding box
            polygon_wkt = (
                f"POLYGON(({min_lng} {min_lat}, "
                f"{min_lng} {max_lat}, "
                f"{max_lng} {max_lat}, "
                f"{max_lng} {min_lat}, "
                f"{min_lng} {min_lat}))"
            )

            zone = LocationZone(
                name=name,
                description=description,
                difficulty=difficulty,
                category=category,
                polygon=WKTElement(polygon_wkt, srid=4326),
                is_active=True,
            )

            session.add(zone)
            await session.flush()

            logger.info(
                f"Created zone '{name}' with bbox ({min_lng},{min_lat},{max_lng},{max_lat})"
            )
            return zone

        except Exception as e:
            logger.error(f"Error creating zone from bbox: {e}")
            await session.rollback()
            return None


# Утилиты для работы с координатами
class CoordinateUtils:
    """Утилиты для работы с географическими координатами"""

    @staticmethod
    def calculate_distance_haversine(
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
    ) -> float:
        """
        Рассчитать расстояние между двумя точками по формуле гаверсинусов.

        Args:
            lon1, lat1: Координаты первой точки
            lon2, lat2: Координаты второй точки

        Returns:
            Расстояние в километрах
        """
        from math import atan2, sqrt

        # Радиус Земли в километрах
        R = 6371.0

        # Конвертируем градусы в радианы
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        # Разницы координат
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        # Формула гаверсинусов
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    @staticmethod
    def calculate_bearing(
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
    ) -> float:
        """
        Рассчитать азимут (направление) от первой точки ко второй.

        Args:
            lon1, lat1: Координаты начальной точки
            lon2, lat2: Координаты конечной точки

        Returns:
            Азимут в градусах (0-360)
        """
        from math import atan2, degrees

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon_rad = radians(lon2 - lon1)

        y = sin(dlon_rad) * cos(lat2_rad)
        x = cos(lat1_rad) * sin(lat2_rad) - sin(lat1_rad) * cos(lat2_rad) * cos(dlon_rad)

        bearing_rad = atan2(y, x)
        bearing_deg = degrees(bearing_rad)

        # Нормализуем к диапазону 0-360
        return (bearing_deg + 360) % 360

    @staticmethod
    def get_random_point_near(
        center_lon: float,
        center_lat: float,
        max_distance_km: float = 10.0,
    ) -> tuple[float, float]:
        """
        Получить случайную точку в радиусе от центра.

        Args:
            center_lon, center_lat: Координаты центра
            max_distance_km: Максимальное расстояние в км

        Returns:
            Кортеж (longitude, latitude)
        """

        # Случайное расстояние (0-max_distance_km)
        distance_km = random.uniform(0, max_distance_km)

        # Случайное направление (0-360 градусов)
        bearing_deg = random.uniform(0, 360)
        bearing_rad = radians(bearing_deg)

        # Радиус Земли в км
        R = 6371.0

        # Угловое расстояние
        angular_distance = distance_km / R

        # Конвертируем координаты центра в радианы
        lat_rad = radians(center_lat)
        lon_rad = radians(center_lon)

        # Вычисляем новые координаты
        new_lat_rad = asin(
            sin(lat_rad) * cos(angular_distance)
            + cos(lat_rad) * sin(angular_distance) * cos(bearing_rad),
        )

        new_lon_rad = lon_rad + atan2(
            sin(bearing_rad) * sin(angular_distance) * cos(lat_rad),
            cos(angular_distance) - sin(lat_rad) * sin(new_lat_rad),
        )

        # Конвертируем обратно в градусы
        new_lat = degrees(new_lat_rad)
        new_lon = degrees(new_lon_rad)

        # Нормализуем долготу к диапазону -180..180
        new_lon = (new_lon + 540) % 360 - 180

        return new_lon, new_lat

    @staticmethod
    def format_coordinates(
        longitude: float,
        latitude: float,
        format: str = "decimal",
    ) -> str:
        """
        Форматировать координаты в различных форматах.

        Args:
            longitude: Долгота
            latitude: Широта
            format: Формат ("decimal", "dms", "verbose")

        Returns:
            Отформатированная строка
        """
        if format == "decimal":
            return f"{latitude:.6f}, {longitude:.6f}"

        if format == "dms":

            def to_dms(coord: float, is_lat: bool) -> str:
                degrees = int(abs(coord))
                minutes_full = (abs(coord) - degrees) * 60
                minutes = int(minutes_full)
                seconds = (minutes_full - minutes) * 60

                direction = ""
                if is_lat:
                    direction = "N" if coord >= 0 else "S"
                else:
                    direction = "E" if coord >= 0 else "W"

                return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"

            lat_str = to_dms(latitude, True)
            lon_str = to_dms(longitude, False)
            return f"{lat_str}, {lon_str}"

        if format == "verbose":
            lat_dir = "северной" if latitude >= 0 else "южной"
            lon_dir = "восточной" if longitude >= 0 else "западной"
            return f"{abs(latitude):.4f}° {lat_dir} широты, {abs(longitude):.4f}° {lon_dir} долготы"

        return f"{latitude:.6f}, {longitude:.6f}"
