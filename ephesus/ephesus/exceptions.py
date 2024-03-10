"""
Exceptions native to the Ephesus project
"""


class AppException(Exception):
    """Parent exception class for custom exceptions raised from this application"""


class InputError(AppException):
    """Error while processing input"""


class BoundsError(AppException):
    """
    Some reference was out of bounds.
    This for is more application
    specific ranges like BCV
    """


class FormatError(AppException):
    """Error related to file format"""


class OutputError(AppException):
    """Error while processing output"""
