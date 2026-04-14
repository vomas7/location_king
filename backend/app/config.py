from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # База данных
    database_url: str

    # Redis
    redis_url: str

    # Keycloak
    keycloak_url: str
    keycloak_realm: str
    keycloak_client_id: str

    # Mapbox (запасной вариант для космических снимков)
    mapbox_access_token: str = ""

    # Приложение
    debug: bool = False

    @property
    def keycloak_jwks_url(self) -> str:
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            f"/protocol/openid-connect/certs"
        )

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"


settings = Settings()
