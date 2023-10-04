"""
CRUD operations for the Home section of the app
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    user_projects as user_projects_model,
)

from . import schemas

# Setup logger
_LOGGER = logging.getLogger(__name__)


def get_user_projects(db: Session, username: str):
    """Get all projects associated with a username"""
    statement = select(user_projects_model.User).where(
        user_projects_model.User.username == username
    )
    user = db.scalars(statement).first()
    _LOGGER.debug(user)

    # projects = sorted(
    #     [
    #         user_projects_model.ProjectDetails(
    #             item.project.resource_id,
    #             item.project.name,
    #             item.project.lang_code,
    #             item.project.create_datetime,
    #         )
    #         for item in current_user.projects
    #     ],
    #     reverse=True,
    #     key=lambda x: x.create_datetime,
    # )


def get_user_projects(db: Session, username: str):
    """Get all projects associated with a username"""
    statement = select(user_projects_model.User).where(
        user_projects_model.User.username == username
    )
    user = db.scalars(statement).first()
    _LOGGER.debug(user)
