"""
Common dependencies useful for the Ephesus application
"""
import logging

from fastapi import (
    Depends,
    Header,
    HTTPException,
    status,
)

from pydantic import ValidationError

from sqlalchemy.orm import Session

from .config import get_ephesus_settings
from .database.crud import (
    is_user_exists,
    create_user,
)
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


async def create_app_user(
    db: Session = Depends(get_db),
    x_forwarded_user: str = Header(),
) -> bool:
    """
    Since auth is handled upstream, any time a new user is
    encountered from the headers, add them into the DB.

    This maybe improved once we figure out a way to get a
    callback from the upstream user registration flow.
    """
    # If user already exists in the DB, skip creation
    if is_user_exists(db, x_forwarded_user):
        return True

    # If user does not exist, create it
    create_user(db, x_forwarded_user)

    return True


async def get_current_user(
    is_app_user_created: bool = Depends(create_app_user),
    x_forwarded_user: str = Header(),
    x_forwarded_email: str | None = Header(None),
    x_forwarded_preferred_username: str | None = Header(None),
) -> AuthenticatedUserModel:
    """
    Get authenticated user details from headers.
    Auth is assumed to be handled upstream by proxy servers
    """
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
