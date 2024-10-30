from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

# App settings
class EphesusSettings(BaseSettings):
    ephesus_env: str
    ephesus_projects_dir: Path
    ephesus_static_results_dir: Path
    ephesus_default_vref_file: Path

    ephesus_email_port: int
    ephesus_email_host: str
    ephesus_support_email: str

    sqlalchemy_database_uri: str

    redis_connection_uri: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_ephesus_settings():
    return EphesusSettings()


# Logging Config
class LogConfig(BaseSettings):
    """Logging configuration to be set for the server"""

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
            "stream": "ext://sys.stdout",
        },
    }
    loggers: dict = {
        "": {"handlers": ["default"], "level": LOG_LEVEL},
    }
