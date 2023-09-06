"""
Model for a user in the ephesus web app
"""

## Imports
import enum
from flask import current_app
from datetime import datetime

# 3rd party imports
from sqlalchemy import Enum
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadSignature, SignatureExpired

# From this project
from web.ephesus.extensions import db
from web.ephesus.constants import StatusType


class User(UserMixin, db.Model):
    """User model for the app"""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))
    name = db.Column(db.String(1000))
    organization = db.Column(db.String(1000))
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
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
