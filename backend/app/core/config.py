from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str
    
    # Configuración de la aplicación
    APP_NAME: str = "La Hidrocálida POS API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Configuración del servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # JWT (para autenticación)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    
    # Zona horaria del restaurante
    TIMEZONE: str = "America/Mexico_City"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Crear instancia global de configuración
settings = Settings()