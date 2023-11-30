from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

# App settings
class EphesusSettings(BaseSettings):
    ephesus_projects_dir: Path
    ephesus_default_vref_file: Path

    sqlalchemy_database_uri: str

    ephesus_client_id: str
    ephesus_client_secret: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_ephesus_settings():
    return EphesusSettings()


# Logging Config
class LogConfig(BaseSettings):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "ephesus"
    LOG_FORMAT: str = "[%(asctime)s] %(levelname)s %(name)s:%(lineno)d -- %(message)s"
    LOG_LEVEL: str = "DEBUG"

    # Logging config
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: dict = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }
