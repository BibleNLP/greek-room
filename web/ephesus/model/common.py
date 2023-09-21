"""
Common resources in support of the application model
"""
# Core Python imports
import logging

# 3rd party imports
# from sqlalchemy.types import TypeDecorator

# From this project
from web.ephesus.extensions import db
from web.ephesus.model.user import Project

_LOGGER = logging.getLogger(__name__)


def get_project_metadata(resource_id):
    """Using the resource_id fetch the Project metadata"""
    return db.session.scalars(
        db.select(Project.project_metadata).where(Project.resource_id == resource_id)
    ).first()


def set_project_metadata(resource_id, project_metadata):
    """Using the resource_id set the Project metadata"""
    if not project_metadata:
        return

    db.session.execute(
        db.update(Project)
        .where(Project.resource_id == resource_id)
        .values(project_metadata=project_metadata)
    )
    db.session.commit()
