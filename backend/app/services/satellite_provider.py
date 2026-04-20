"""
Сервис для работы с космическими снимками.
Поддерживает разные провайдеры (ESRI World Imagery, Mapbox, Sentinel-2, etc.)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SatelliteImage:
    """Результат запроса космического снимка"""

    image_url: str  # URL для загрузки изображения
    bounds: tuple[float, float, float, float]  # [west, south, east, north]
    center: tuple[float, float]  # [lng, lat]
    provider: str  # Название провайдера
    metadata: dict  # Дополнительные метаданные


class BaseSatelliteProvider(ABC):
    """Базовый класс для всех провайдеров космических снимков"""

    @abstractmethod
    async def get_satellite_image(
        self,
        center_lng: float,
        center_lat: float,
        width_km: int = 5,
        height_km: int = 5,
    ) -> SatelliteImage | None:
        """
        Получить космический снимок для заданной области.

        Args:
            center_lng: Долгота центра области
            center_lat: Широта центра области
            width_km: Ширина области в километрах
            height_km: Высота области в километрах

        Returns:
            SatelliteImage или None в случае ошибки
        """

    @staticmethod
    def _calculate_bounds(
        center_lng: float,
        center_lat: float,
        width_km: int,
        height_km: int,
    ) -> tuple[float, float, float, float]:
        """
        Рассчитать границы области в градусах по размерам в километрах.
        Упрощённый расчёт (для небольших областей).
        """
        # Примерное преобразование: 1° широты ≈ 111 км
        # 1° долготы ≈ 111 км * cos(широта)
        import math
        lat_deg_per_km = 1 / 111.0
        lat_rad = math.radians(center_lat)
        cos_lat = max(abs(math.cos(lat_rad)), 0.0001)  # защита от нуля
        lng_deg_per_km = 1 / (111.0 * cos_lat)

        half_width_deg = (width_km / 2) * lng_deg_per_km
        half_height_deg = (height_km / 2) * lat_deg_per_km

        west = center_lng - half_width_deg
        east = center_lng + half_width_deg
        south = center_lat - half_height_deg
        north = center_lat + half_height_deg

        return west, south, east, north


class ESRISatelliteProvider(BaseSatelliteProvider):
    """Провайдер космических снимков ESRI World Imagery"""

    def __init__(self):
        self.base_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_satellite_image(
        self,
        center_lng: float,
        center_lat: float,
        width_km: int = 5,
        height_km: int = 5,
    ) -> SatelliteImage | None:
        """
        Получить статичное изображение со спутника от ESRI World Imagery.

        ESRI World Imagery: https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer
        """
        try:
            # Рассчитываем границы области
            bounds = self._calculate_bounds(center_lng, center_lat, width_km, height_km)
            west, south, east, north = bounds

            # Для ESRI нам нужно рассчитать зум и координаты тайла
            # Используем приблизительный расчёт для зума 15 (хорошая детализация)
            zoom = 15

            # Конвертируем координаты в тайлы
            tile_x, tile_y = self._lnglat_to_tile(center_lng, center_lat, zoom)

            # Формируем URL тайла
            tile_url = self.base_url.format(z=zoom, y=tile_y, x=tile_x)

            # Для фронтенда создаём URL шаблон
            tile_template = self.base_url

            return SatelliteImage(
                image_url=tile_template,  # Шаблон URL для фронтенда
                bounds=bounds,
                center=(center_lng, center_lat),
                provider="esri",
                metadata={
                    "tile_url": tile_url,
                    "zoom": zoom,
                    "tile_x": tile_x,
                    "tile_y": tile_y,
                    "width_km": width_km,
                    "height_km": height_km,
                    "bounds": bounds,
                    "attribution": "© Esri, Maxar, Earthstar Geographics, and the GIS User Community",
                },
            )

        except Exception as e:
            logger.error(f"ESRI provider error: {e}")
            return None

    @staticmethod
    def _lnglat_to_tile(lng: float, lat: float, zoom: int) -> tuple[int, int]:
        """Конвертировать координаты в номер тайла"""
        import math

        # Формула конвертации координат в тайлы
        n = 2.0**zoom
        lat_rad = math.radians(lat)
        x = int((lng + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

        return x, y

    async def close(self):
        """Закрыть HTTP-клиент"""
        await self.client.aclose()


class MapboxSatelliteProvider(BaseSatelliteProvider):
    """Провайдер космических снимков Mapbox (запасной вариант)"""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or settings.mapbox_access_token
        self.base_url = "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_satellite_image(
        self,
        center_lng: float,
        center_lat: float,
        width_km: int = 5,
        height_km: int = 5,
    ) -> SatelliteImage | None:
        """
        Получить статичное изображение со спутника от Mapbox.

        Mapbox Static API: https://docs.mapbox.com/api/maps/static-images/
        """
        try:
            # Рассчитываем границы области
            bounds = self._calculate_bounds(center_lng, center_lat, width_km, height_km)
            west, south, east, north = bounds

            # Формируем bounding box строку для Mapbox
            bbox = f"{west},{south},{east},{north}"

            # Параметры запроса
            params = {
                "access_token": self.access_token,
                "bbox": bbox,
                "width": 800,  # Размер изображения
                "height": 600,
                "attribution": "false",
                "logo": "false",
            }

            # Формируем URL
            url = f"{self.base_url}/[{bbox}]/{params['width']}x{params['height']}"

            # Делаем запрос
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            # Mapbox возвращает бинарное изображение
            # Для статичного API нам нужен URL, а не само изображение
            # Создаём URL, который клиент сможет использовать напрямую
            image_url = str(response.url)

            return SatelliteImage(
                image_url=image_url,
                bounds=bounds,
                center=(center_lng, center_lat),
                provider="mapbox",
                metadata={
                    "width_px": params["width"],
                    "height_px": params["height"],
                    "width_km": width_km,
                    "height_km": height_km,
                },
            )

        except httpx.HTTPError as e:
            logger.error(f"Mapbox API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Mapbox provider: {e}")
            return None

    async def close(self):
        """Закрыть HTTP-клиент"""
        await self.client.aclose()


class SentinelSatelliteProvider(BaseSatelliteProvider):
    """Провайдер космических снимков Sentinel-2 (ESA Copernicus)"""

    def __init__(self):
        # TODO: Реализовать интеграцию с Sentinel Hub
        self.base_url = "https://services.sentinel-hub.com/ogc/wms"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_satellite_image(
        self,
        center_lng: float,
        center_lat: float,
        width_km: int = 5,
        height_km: int = 5,
    ) -> SatelliteImage | None:
        """
        Получить снимок Sentinel-2.
        Требуется настройка Sentinel Hub и instance ID.
        """
        # TODO: Реализовать интеграцию с Sentinel Hub API
        logger.warning("Sentinel-2 provider not implemented yet")
        return None

    async def close(self):
        await self.client.aclose()


# Фабрика для создания провайдеров
class SatelliteProviderFactory:
    """Фабрика для создания провайдеров космических снимков"""

    @staticmethod
    def create_provider(provider_name: str = "mapbox", **kwargs) -> BaseSatelliteProvider:
        """
        Создать провайдера космических снимков.

        Args:
            provider_name: Имя провайдера ("mapbox", "sentinel")
            **kwargs: Дополнительные параметры для провайдера

        Returns:
            Экземпляр провайдера
        """
        providers = {
            "esri": ESRISatelliteProvider,
            "mapbox": MapboxSatelliteProvider,
            "sentinel": SentinelSatelliteProvider,
        }

        provider_class = providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unknown satellite provider: {provider_name}")

        return provider_class(**kwargs)


# Глобальный экземпляр провайдера (можно использовать как синглтон)
_satellite_provider: BaseSatelliteProvider | None = None


async def get_satellite_provider() -> BaseSatelliteProvider:
    """
    Получить глобальный экземпляр провайдера космических снимков.
    Использует Mapbox по умолчанию.
    """
    global _satellite_provider

    if _satellite_provider is None:
        # Используем ESRI World Imagery как провайдер по умолчанию (бесплатный)
        _satellite_provider = SatelliteProviderFactory.create_provider("esri")

    return _satellite_provider


async def close_satellite_provider():
    """Закрыть глобальный провайдер"""
    global _satellite_provider

    if _satellite_provider:
        await _satellite_provider.close()
        _satellite_provider = None
