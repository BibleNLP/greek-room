"""Utils for the Auth blueprint"""

# Imports
## Core Python
import re
import logging

## Third party
import flask

# Logger
_LOGGER = logging.getLogger(__name__)


def is_valid_password(password):
    """
    Check if password is of acceptable standard
    This is to be in-sync with the UI validation.
    This is needed if anyone tries to bypass the UI.
    """
    # Currently only check if it is 8 chars long
    if len(password) > 7 and len(password) < 101:
        return True

    return False


def is_valid_username(username):
    """
    Check if password is of acceptable standard.
    This is to be in-sync with the UI validation.
    This is needed if anyone tries to bypass the UI.
    """
    # Match for valid username pattern
    if re.match(r"[a-z0-9]{3,50}", username):
        return True

    return False


def is_project_op_permitted(username, roles, project_meta, op="read"):
    """
    A central function for simple role-based
    checking for project operation
    """
    if not username or not roles or not project_meta:
        return False

    if username == project_meta.get("owner", ""):
        return True

    tags = set(project_meta.get("tags", []))
    roles = set(roles)
    acl = flask.current_app.config["acl"]

    for tag in tags.intersection(acl.keys()):
        for role in roles:
            if role in acl.get(tag, {}).get(op, []):
                return True

    return False
