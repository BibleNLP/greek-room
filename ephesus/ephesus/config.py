from contextlib import asynccontextmanager
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any
import logging
import json

from fastapi import FastAPI

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

from .constants import (
    GlobalStates,
)

# logging
_LOGGER = logging.getLogger(__name__)

# App settings
class EphesusSettings(BaseSettings):
    ephesus_env: str
    ephesus_projects_dir: Path
    ephesus_default_vref_file: Path

    sqlalchemy_database_uri: str

    redis_connection_uri: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_ephesus_settings():
    return EphesusSettings()


@lru_cache
def get_global_state(key: GlobalStates) -> Any | None:
    """
    Create a global state for the app
    which holds random (small) stuff
    that is useful across multiple parts
    """
    # Keep the initialization inline
    # since the get is optimized/memoized
    # via the @lru_cache decorater
    state: dict[GlobalStates, Any] = {}

    # Add the vref index
    with get_ephesus_settings().ephesus_default_vref_file.with_suffix(".index").open() as index_file:
        state[GlobalStates.VREF_INDEX.value] = json.load(index_file)

    return state.get(key.value, None)


def index_vref() -> None:
    """Create index for the vref.txt file"""
    if not get_ephesus_settings().ephesus_default_vref_file.exists():
        raise AppException("Unable to find the default vref.txt file")

    # Re-use existing index file, if it already exists
    if get_ephesus_settings().ephesus_default_vref_file.with_suffix(".index").exists():
        _LOGGER.info("Skipped creating and reusing existing vref.index")
    else:
        _LOGGER.info("Creating vref.index")
        vref_idx_map: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(lambda: [-1, -1]))
        with get_ephesus_settings().ephesus_default_vref_file.open() as vref_file, get_ephesus_settings().ephesus_default_vref_file.with_suffix(
            ".index"
        ).open(
            "w"
        ) as index_file:
            for idx, line in enumerate(vref_file):
                line: str = line.strip()
                if not line:
                    continue

                book: str = line.split()[0]
                chapter: str = line.split()[1].split(":")[0]

                ## Write out start and end indices
                # Start condition
                if len(vref_idx_map) == 0:
                    vref_idx_map[book][chapter][0] = idx
                    prev_book: str = book
                    prev_chapter: str = chapter
                    continue

                if book not in vref_idx_map or chapter not in vref_idx_map[book]:
                    vref_idx_map[prev_book][prev_chapter][1] = idx-1
                    vref_idx_map[book][chapter][0] = idx
                    prev_book = book
                    prev_chapter = chapter

            # End condition
            vref_idx_map[book][chapter][1] = idx

            json.dump(vref_idx_map, index_file)


# App lifespan initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Custom startup and shutdown logic.

    On startup:
    - Create an index for the vref.txt file

    On shutdown:
    - Noop
    """
    index_vref()

    yield

    ## On shutdown
    # Noop

# @app.on_event("startup")
# async def populate_seed_data():
#     """Setup seed data for development"""
#     # This is here to avoid circular imports
#     from .database.models.user_projects import (
#         User,
#         Project,
#         ProjectAccess,
#     )
#     from .database.seed import seed_data

#     # This method receives a table, a connection
#     # and inserts data to that table.
#     def seed_table(target, connection, **kw):
#         tablename = str(target)
#         if tablename in seed_data and len(seed_data[tablename]) > 0:
#             connection.execute(target.insert(), seed_data[tablename])

#     _LOGGER.debug("Populating seed data in app database")
#     sqlalchemy_listen(User.__table__, "after_create", seed_table)
#     sqlalchemy_listen(Project.__table__, "after_create", seed_table)
#     sqlalchemy_listen(ProjectAccess.__table__, "after_create", seed_table)



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
            "stream": "ext://sys.stdout",
        },
    }
    loggers: dict = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL},
    }
