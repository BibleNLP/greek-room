"""Utils for the Auth blueprint"""

# Imports
## Core Python
import re


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
