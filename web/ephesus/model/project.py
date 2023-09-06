"""
Model for projects in the ephesus web app
"""

## Imports
from flask import current_app
from datetime import datetime

# 3rd party imports
from sqlalchemy import Enum

# From this project
from web.ephesus.extensions import db
from web.ephesus.constants import (
    ProjectAccessType,
    StatusType,
)
from web.ephesus.model.user import User

# {"projectName": "lao", "langCode": "lao", "wbAnalysisLastModified": 1683586139.3936162, "projectType": "wildebeest", "tags": "[]", "owner": "bob"}


class Project(db.Model):
    """Model to hold project specific information"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    lang_code = db.Column(db.String(10))
    tags = db.Column(db.JSON, default=[])
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(Enum(StatusType), default=StatusType.ACTIVE.name)

    # Store arbitary project metadata
    project_metadata = db.Column(db.JSON, default={})

    users = db.relationship("ProjectAccess", back_populates="project")


# Join table for NxN relationship between
# Users and Projects tables
class ProjectAccess(db.Model):
    """Model to connect Users with Projects based on permissions and store metadata"""

    id = db.Column(db.Integer, primary_key=True)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))

    user = db.relationship("User", back_populates="projects")
    project = db.relationship("Project", back_populates="users")

    access_type = db.Column(
        Enum(ProjectAccessType), default=ProjectAccessType.OWNER.name
    )
