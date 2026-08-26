"""Настройки приложения. Все значения приходят из переменных окружения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Хранилища ────────────────────────────────────────────────────────
    database_url: str
    redis_url: str

    # ── JWT ──────────────────────────────────────────────────────────────
    # Дефолта нет намеренно: без секрета приложение не должно стартовать.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # ── Спутниковые снимки ───────────────────────────────────────────────
    # Шаблон тайлового сервера. Тайлы отдаются клиенту только через прокси
    # backend'а, чтобы координаты цели не утекали.
    satellite_tile_url: str = (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}"
    )
    satellite_attribution: str = "Esri, Maxar, Earthstar Geographics"
    satellite_max_zoom: int = 18
    tile_cache_ttl_seconds: int = 7 * 24 * 3600
    tile_request_timeout_seconds: float = 15.0

    # ── Приложение ───────────────────────────────────────────────────────
    # Список origin'ов через запятую: pydantic-settings разбирает list[str] как
    # JSON, поэтому храним строкой и разбираем сами.
    cors_origins: str = "http://localhost:8080"
    debug: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        """Разрешённые origin'ы для CORS."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
