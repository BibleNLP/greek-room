"""
CRUD operations for the Home section of the app
"""
import logging

from sqlalchemy import select, update
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


def create_user(db: Session, username: str) -> None:
    """Create a user in the app database"""
    db.add(User(username=username))
    db.commit()


def is_user_exists(db: Session, username: str) -> bool:
    """Check if a user exists in the app database"""
    return db.scalars(select(User).where(User.username == username)).first() is not None


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


def update_user_project_metadata(
    db: Session, resource_id: str, metadata: dict
) -> None:
    """Update the metadata for the project `resource_id`"""
    project = db.scalars(
        (select(Project).where(Project.resource_id == resource_id))
    ).first()

    db.execute(
        (
            update(Project)
            .where(Project.resource_id == resource_id)
            .values(project_metadata={**project.project_metadata, **metadata})
        )
    )


def create_user_project(
    db: Session,
    project_name: str,
    resource_id: str,
    lang_code: str,
    username: str,
    project_metadata: dict = {},
) -> None:
    """Create a project entry in the DB for a user"""
    user = db.scalars((select(User).where(User.username == username))).first()
    project = Project(
        resource_id=resource_id,
        name=project_name,
        lang_code=lang_code,
        project_metadata=project_metadata,
    )
    project_access = ProjectAccess(
        project=project,
        user=user,
        access_type=ProjectAccessType.OWNER.name,
    )
    project.users.append(project_access)
    db.add(project)
    db.commit()


def delete_project(
    db: Session,
    resource_id: str,
) -> None:
    """Cascade delete a project entry from the DB.
    WARNING: This function does not check for business
    logic (e.g. access_type requirements, etc.). Those
    are delegated to the caller. This is indescriminate!"""

    project = db.scalars(
        (select(Project).where(Project.resource_id == resource_id))
    ).first()
    project_access = db.scalars(
        (select(ProjectAccess).where(ProjectAccess.project_id == project.id))
    )

    # Delete project_access and project instances
    for projec_access_entry in project_access:
        db.delete(projec_access_entry)

    db.delete(project)

    db.commit()
