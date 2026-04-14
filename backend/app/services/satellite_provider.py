"""
Сервис для работы с космическими снимками.
Поддерживает разные провайдеры (Mapbox, Sentinel-2, etc.)
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

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
    ) -> Optional[SatelliteImage]:
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
        pass
    
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
        lat_deg_per_km = 1 / 111.0
        lng_deg_per_km = 1 / (111.0 * abs(center_lat))
        
        half_width_deg = (width_km / 2) * lng_deg_per_km
        half_height_deg = (height_km / 2) * lat_deg_per_km
        
        west = center_lng - half_width_deg
        east = center_lng + half_width_deg
        south = center_lat - half_height_deg
        north = center_lat + half_height_deg
        
        return west, south, east, north


class MapboxSatelliteProvider(BaseSatelliteProvider):
    """Провайдер космических снимков Mapbox"""
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.mapbox_access_token
        self.base_url = "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_satellite_image(
        self,
        center_lng: float,
        center_lat: float,
        width_km: int = 5,
        height_km: int = 5,
    ) -> Optional[SatelliteImage]:
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
                }
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
    ) -> Optional[SatelliteImage]:
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
            "mapbox": MapboxSatelliteProvider,
            "sentinel": SentinelSatelliteProvider,
        }
        
        provider_class = providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unknown satellite provider: {provider_name}")
        
        return provider_class(**kwargs)


# Глобальный экземпляр провайдера (можно использовать как синглтон)
_satellite_provider: Optional[BaseSatelliteProvider] = None


async def get_satellite_provider() -> BaseSatelliteProvider:
    """
    Получить глобальный экземпляр провайдера космических снимков.
    Использует Mapbox по умолчанию.
    """
    global _satellite_provider
    
    if _satellite_provider is None:
        # Пока используем Mapbox как провайдер по умолчанию
        _satellite_provider = SatelliteProviderFactory.create_provider("mapbox")
    
    return _satellite_provider


async def close_satellite_provider():
    """Закрыть глобальный провайдер"""
    global _satellite_provider
    
    if _satellite_provider:
        await _satellite_provider.close()
        _satellite_provider = None