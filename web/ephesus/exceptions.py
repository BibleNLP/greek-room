"""
Exceptions native to this project
"""


class AppException(Exception):
    """Parent exception class for custom exceptions raised from this application"""


class InternalError(AppException):
    """Blueprint specific errors"""


class InputError(AppException):
    """Error while processing input"""
