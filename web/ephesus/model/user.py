"""
Model for a user in the ephesus web app
"""

## Imports
from flask import current_app
from datetime import datetime

# 3rd party imports
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer

# from this project
from web.ephesus.extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(1000))
    name = db.Column(db.String(1000))
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_email_verified = db.Column(db.Boolean(), default=False)

    def get_email_verification_token(self):
        serializer = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"], salt="email-verification"
        )
        return serializer.dumps(self.email)

    @staticmethod
    def verify_email_token(token):
        try:
            serializer = URLSafeTimedSerializer(
                current_app.config["SECRET_KEY"], salt="email-verification"
            )

            # Load token with expiry
            email = serializer.loads(token, max_age=600)

            return email
        except (SignatureExpired, BadSignature):
            return None
