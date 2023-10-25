"""
Exceptions native to the Ephesus project
"""


class AppException(Exception):
    """Parent exception class for custom exceptions raised from this application"""


class InputError(AppException):
    """Error while processing input"""
