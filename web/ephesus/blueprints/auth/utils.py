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


# Roles are implemented based on https://tailscale.com/blog/rbac-like-it-was-meant-to-be/
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
