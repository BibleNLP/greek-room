"""
CRUD operations for the Home section of the app
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.user_projects import (
    User,
    Project,
    ProjectAccess,
)
from . import schemas


# Setup logger
_LOGGER = logging.getLogger(__name__)


def get_user_projects(
    db: Session, username: str
) -> list[schemas.ProjectListModel] | None:
    """Get all projects associated with a username"""
    projects = db.scalars(
        select(Project)
        .join(ProjectAccess)
        .where(Project.id == ProjectAccess.project_id)
        .join(User)
        .where(User.username == username)
    ).all()
    return projects


def get_user_project_details(db: Session, resource_id: str, username: str):
    """Get the overview of `resource_id` project"""
    # Check if the requested project is accessible to the user
    # This returns `Project` instance as the first result
    # and the `ProjectAccess.access_type` as the second result
    # both in the same tuple.
    statement = select(User).where(User.username == username)
    current_user = db.scalars(statement).first()

    project_details = db.execute(
        (
            select(Project, ProjectAccess.access_type)
            .join(ProjectAccess)
            .where(ProjectAccess.user_id == current_user.id)
            .where(Project.resource_id == resource_id)
        )
    ).first()

    _LOGGER.debug(project_details)

    return project_details


# def get_user_projects(db: Session, username: str):
#     """Get all projects associated with a username"""
#     statement = select(user_projects_model.User).where(
#         user_projects_model.User.username == username
#     )
#     user = db.scalars(statement).first()
#     _LOGGER.debug(user)
