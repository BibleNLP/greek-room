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
    return db.scalars(
        select(Project)
        .join(ProjectAccess)
        .where(Project.id == ProjectAccess.project_id)
        .join(User)
        .where(User.username == username)
    ).all()


def get_user_project(
    db: Session, resource_id: str, username: str
) -> schemas.ProjectWithAccessModel | None:
    """Get the overview of `resource_id` project"""
    # Check if the requested project is accessible to the user
    # This returns `Project` instance as the first result
    # and the `ProjectAccess.access_type` as the second result
    # both in the same tuple.
    statement = select(User).where(User.username == username)
    current_user = db.scalars(statement).first()

    project = db.execute(
        (
            select(Project, ProjectAccess)
            .join(ProjectAccess)
            .where(ProjectAccess.user_id == current_user.id)
            .where(Project.resource_id == resource_id)
        )
    ).first()
    return None if not project else project._mapping
