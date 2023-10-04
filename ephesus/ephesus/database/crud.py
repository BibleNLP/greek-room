"""
CRUD operations for the Home section of the app
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas

# Setup logger
_LOGGER = logging.getLogger(__name__)


def get_user_projects(db: Session, username: str):
    """Get all projects associated with a username"""
    statement = select(models.User).where(models.User.username == username)
    user = db.scalars(statement).first()
    _LOGGER.debug(user)

    # projects = sorted(
    #     [
    #         models.ProjectDetails(
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
