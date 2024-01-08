"""
Common dependencies useful for the Ephesus application
"""
import logging
from typing import Annotated

from fastapi import (
    Depends,
    Header,
)

from sqlalchemy.orm import Session

import redis.asyncio as redis

from .config import get_ephesus_settings
from .database.crud import (
    is_user_exists,
    create_user,
)
from .database.setup import (
    SessionLocal,
    redis_conn_pool,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# Get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_cache():
    cache = redis.Redis(connection_pool=redis_conn_pool)
    try:
        yield cache
    finally:
        await cache.aclose()


async def create_app_user(
    x_forwarded_preferred_username: Annotated[str, Header(include_in_schema=False)],
    db: Session = Depends(get_db),
) -> bool:
    """
    Since auth is handled upstream, any time a new user is
    encountered from the headers, add them into the DB.

    Note: This maybe improved once we figure out a way to
    get a callback from the upstream user registration flow.
    """
    # If user already exists in the DB, skip creation
    if is_user_exists(db, x_forwarded_preferred_username):
        return True

    # If user does not exist, create it
    create_user(db, x_forwarded_preferred_username)

    return True


async def get_current_username(
    x_forwarded_preferred_username: Annotated[str, Header(include_in_schema=False)],
    is_app_user_created: bool = Depends(create_app_user),
    # x_forwarded_user: str = Header(),
    # x_forwarded_email: str | None = Header(None),
) -> str:
    """
    Get authenticated user details from headers.
    Auth is assumed to be handled upstream by proxy servers
    """
    return x_forwarded_preferred_username
