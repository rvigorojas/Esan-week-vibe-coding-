"""
Configuracion de la aplicacion, leida desde variables de entorno.
Ver .env.example / _env.example para las claves esperadas.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pce:pce@localhost:5432/pce"
    jwt_secret: str = "cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    # Token blando (ADR-7): ventana maxima en la que el cliente PMM sigue
    # aceptando y encolando acciones con el token vencido mientras esta offline.
    # Al reconectar, el backend acepta lo ya encolado si sigue dentro de esta ventana.
    jwt_soft_token_grace_hours: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()
