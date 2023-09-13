"""
Model for a user in the ephesus web app
"""

## Imports
import secrets
from datetime import datetime, timezone

# 3rd party imports
from sqlalchemy import Enum
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadSignature, SignatureExpired

# From this project
from web.ephesus.extensions import db
from web.ephesus.constants import (
    ProjectAccessType,
    StatusType,
)
from web.ephesus.model.common import (
    TZDateTime,
)


class User(UserMixin, db.Model):
    """User model for the app"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))
    name = db.Column(db.String(1000))
    organization = db.Column(db.String(1000))
    create_datetime = db.Column(
        TZDateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    update_datetime = db.Column(
        TZDateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    is_email_verified = db.Column(db.Boolean(), default=False)
    status = db.Column(Enum(StatusType), default=StatusType.ACTIVE.name)
    roles = db.Column(db.JSON, default=["public"])

    projects = db.relationship("ProjectAccess", back_populates="user")

    def get_email_verification_token(self):
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt="email-verification"
        )
        return serializer.dumps(self.email)

    def get_reset_password_token(self):
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt="reset-password"
        )
        return serializer.dumps(self.email)

    @staticmethod
    def decrypt_email_token(token, salt):
        try:
            serializer = URLSafeTimedSerializer(
                current_app.config["SECRET_KEY"], salt=salt
            )

            # Load token with expiry (10m)
            email = serializer.loads(token, max_age=600)

            return email
        except (SignatureExpired, BadSignature):
            return None


class Project(db.Model):
    """Model to hold project specific information"""

    id = db.Column(db.Integer, primary_key=True)

    # Human-and-URL-friendly ID
    resource_id = db.Column(db.String(50), default=secrets.token_urlsafe(6))
    name = db.Column(db.String(1000))
    lang_code = db.Column(db.String(10))
    tags = db.Column(db.JSON, default=[])
    status = db.Column(Enum(StatusType), default=StatusType.ACTIVE.name)
    create_datetime = db.Column(
        TZDateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    update_datetime = db.Column(
        TZDateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Store arbitary project metadata
    project_metadata = db.Column(db.JSON, default={})

    users = db.relationship("ProjectAccess", back_populates="project")


# Join table for NxN relationship between
# Users and Projects tables
class ProjectAccess(db.Model):
    """Model to connect Users with Projects based on permissions and store metadata"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))
    create_datetime = db.Column(
        TZDateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    update_datetime = db.Column(
        TZDateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="projects")
    project = db.relationship("Project", back_populates="users")

    access_type = db.Column(
        Enum(ProjectAccessType), default=ProjectAccessType.OWNER.name
    )
