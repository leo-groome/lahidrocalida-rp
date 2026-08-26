from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str

    # Configuración de la aplicación
    APP_NAME: str = "La Hidrocálida POS API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Configuración del servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # JWT (para autenticación)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # Orígenes permitidos por CORS, separados por coma. Sin default: cada entorno
    # (local, Railway) declara los suyos explícitamente en su .env.
    CORS_ORIGINS: str

    # Zona horaria del restaurante
    TIMEZONE: str = "America/Mexico_City"

    # Redis: fan-out de eventos WS entre workers/réplicas y backend del rate
    # limiter (S2). None = degradar a fan-out local / rate limit en memoria.
    REDIS_URL: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Instancia global de configuración (cacheada)
settings = get_settings()
