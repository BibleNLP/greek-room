"""
Exceptions native to this project
"""

import flask


class AppException(Exception):
    """Parent exception class for custom exceptions raised from this application"""


class InternalError(AppException):
    """Blueprint specific errors"""


class InputError(AppException):
    """Error while processing input"""


class ProjectError(AppException):
    """Error specific to project"""


def internal_server_error(e):
    return flask.render_template("500.html"), 500
