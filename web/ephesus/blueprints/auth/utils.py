"""Utils for the Auth blueprint"""

# Imports
## Core Python
import re
import logging

## Third party
import flask

# This project
from web.ephesus.extensions import db
from web.ephesus.constants import (
    ProjectAcessRights,
    ProjectAccessType,
)
from web.ephesus.model.user import User, Project, ProjectAccess


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


# Roles are implemented based on https://tailscale.com/blog/rbac-like-it-was-meant-to-be/
def is_project_op_permitted(username, resource_id, op=ProjectAcessRights.READ.name):
    """
    A central function for simple role-based
    checking for project operation
    """
    if not username or not resource_id:
        return False

    row = db.session.execute(
        db.select(User, ProjectAccess)
        .join(ProjectAccess)
        .join(Project)
        .where(User.username == username)
        .where(Project.resource_id == resource_id)
    ).first()

    if row and len(row) == 2:
        # Check if the user is the project owner
        if row[1].access_type == ProjectAccessType.OWNER:
            return True
    # Failure to retrieve data from DB
    else:
        _LOGGER.debug("Could not retrieve user access data from DB")
        return False

    # TODO: Handle policy based on ACL from DB
    tags = set(project_meta.get("tags", []))
    roles = set(roles)
    acl = flask.current_app.config["acl"]

    for tag in tags.intersection(acl.keys()):
        for role in roles:
            if role in acl.get(tag, {}).get(op, []):
                return True

    return False


def is_op_permitted(username, user_roles, op_tags, ops=["read"]):
    """
    A central function for simple role-based
    checking for generic app-level operations.
    Checks if `op is allowed for any role in
    `op_tags` by `user_roles`.
    """
    if not username or not user_roles or not op_tags:
        return False

    op_tags = set(op_tags)
    acl = flask.current_app.config["acl"]

    # A list to hold the permission
    # status for each op (e.g. Read/Write).
    # This traverses all user roles and
    # attempts to satisfy all ops.
    ops_perms = []

    for tag in op_tags.intersection(acl.keys()):
        for role in user_roles:
            for op in ops:
                ops_perms.append(role in acl.get(tag, {}).get(op, []))

                # Check if all ops are permitted
                if sum(ops_perms) == len(ops):
                    return True

    return False
