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
from ..constants import ProjectAccessType

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


def create_user_project(
    db: Session,
    project_name: str,
    resource_id: str,
    lang_code: str,
    username: str,
) -> None:
    """Create a project entry in the DB for a user"""
    _LOGGER.debug(username)
    user = db.scalars((select(User).where(User.username == username))).first()
    project = Project(
        resource_id=resource_id,
        name=project_name,
        lang_code=lang_code,
    )
    _LOGGER.debug(user)
    project_access = ProjectAccess(
        project=project,
        user=user,
        access_type=ProjectAccessType.OWNER.name,
    )
    project.users.append(project_access)
    db.add(project)
    db.commit()
