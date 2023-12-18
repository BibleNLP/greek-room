"""
Common dependencies useful for the Ephesus application
"""
import logging

from fastapi import (
    Header,
    HTTPException,
    status,
)

from pydantic import ValidationError

from .config import get_ephesus_settings
from .database.setup import SessionLocal
from .database.schemas import (
    AuthenticatedUserModel,
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


def get_current_user(
    x_forwarded_user: str = Header(),
    x_forwarded_email: str | None = Header(None),
    x_forwarded_preferred_username: str | None = Header(None),
) -> AuthenticatedUserModel:
    try:
        authenticated_user = AuthenticatedUserModel(
            username=x_forwarded_user, email=x_forwarded_email
        )
    except ValidationError as exc:
        _LOGGER.exception(exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find username. Please login and try again.",
        )
    return authenticated_user
