"""
Чистые географические функции: расстояния и арифметика тайлов Web Mercator.

Единственный источник истины по геометрии в проекте. Зависимостей от БД нет.
"""

import math

# Радиус Земли, км
EARTH_RADIUS_KM = 6371.0088

# Длина экватора, км — по ней считается ширина тайла
EQUATOR_KM = 2 * math.pi * EARTH_RADIUS_KM

# Предел широты в проекции Web Mercator
MAX_MERCATOR_LAT = 85.05112878


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Расстояние между двумя точками в километрах по формуле гаверсинусов."""
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    d_lat = lat2_rad - lat1_rad
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    """Номер тайла Web Mercator (XYZ), в котором лежит точка."""
    lat = max(min(lat, MAX_MERCATOR_LAT), -MAX_MERCATOR_LAT)
    n = 2**zoom

    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tile_bounds(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    """Границы тайла (west, south, east, north) в градусах."""
    n = 2**zoom

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))

    return west, south, east, north


def tile_center(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Центр тайла в градусах (lon, lat)."""
    west, south, east, north = tile_bounds(x, y, zoom)
    return (west + east) / 2, (south + north) / 2


def tile_width_km(x: int, y: int, zoom: int) -> float:
    """Ширина тайла в километрах на широте его центра."""
    _, lat = tile_center(x, y, zoom)
    return EQUATOR_KM * math.cos(math.radians(lat)) / 2**zoom


def zoom_for_extent(lat: float, extent_km: float, min_zoom: int = 3, max_zoom: int = 17) -> int:
    """
    Подобрать зум, на котором тайл ближе всего по ширине к заданному размеру области.

    Ширина тайла на широте lat: EQUATOR_KM * cos(lat) / 2^zoom.
    """
    lat = max(min(lat, MAX_MERCATOR_LAT), -MAX_MERCATOR_LAT)
    span_km = EQUATOR_KM * math.cos(math.radians(lat))

    zoom = round(math.log2(span_km / extent_km))
    return min(max(zoom, min_zoom), max_zoom)
