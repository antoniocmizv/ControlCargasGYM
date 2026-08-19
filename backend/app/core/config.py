from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "clave-de-desarrollo-no-usar-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    database_url: str = "sqlite:///./cargas.db"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    coach_username: str = "entrenador"
    coach_password: str = "cambiame"
    coach_name: str = "Entrenador"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
