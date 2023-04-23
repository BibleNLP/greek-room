"""
Model for a user in the ephesus web app
"""

## Imports
# 3rd party imports
from flask_login import UserMixin

# from this project
from web.ephesus.extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
