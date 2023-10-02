"""
Constants used in this application
"""
from enum import Enum, unique, EnumMeta
from collections import namedtuple

# Enums
class MyEnumMeta(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        else:
            return True


@unique
class ProjectTypes(Enum, metaclass=MyEnumMeta):
    """
    All project types supported in this application
    """

    PROJ_WILDEBEEST = "wildebeest"


class StatusType(Enum):
    """Generic app status types"""

    ACTIVE = 1  # Regular operational status
    INACTIVE = 2  # Deleted by user
    DISABLED = 3  # Deleted by someone other than the account owner


class ProjectAccessType(Enum):
    """Types of access a user has on a project"""

    OWNER = 1  # The person who created the project
    COLLABORATOR = 2  # Has both read/write except some sensitive attributes.
    VIEWER = 3  # Only allowed to read things. No write.


class ProjectAcessRights(Enum):
    """Rights of access a user has on a project.
    This is a bit redundant but still useful."""

    READ = 1  # Has the read access on the project
    WRITE = 2  # Has the write access on the project


# Wrapper for sending project data to frontend
ProjectDetails = namedtuple(
    "ProjectDetails", ["resource_id", "project_name", "lang_code", "create_datetime"]
)

# The String to call the 'latest' version of the project
LATEST_PROJECT_VERSION_NAME = "latest"


@unique
class BookCodes(Enum, metaclass=MyEnumMeta):
    """
    All Bible books 3-letter codes.
    66 books in all.
    """

    BOOK_GEN = "GEN"
    BOOK_EXO = "EXO"
    BOOK_LEV = "LEV"
    BOOK_NUM = "NUM"
    BOOK_DEU = "DEU"
    BOOK_JOS = "JOS"
    BOOK_JDG = "JDG"
    BOOK_RUT = "RUT"
    BOOK_1SA = "1SA"
    BOOK_2SA = "2SA"
    BOOK_1KI = "1KI"
    BOOK_2KI = "2KI"
    BOOK_1CH = "1CH"
    BOOK_2CH = "2CH"
    BOOK_EZR = "EZR"
    BOOK_NEH = "NEH"
    BOOK_EST = "EST"
    BOOK_JOB = "JOB"
    BOOK_PSA = "PSA"
    BOOK_PRO = "PRO"
    BOOK_ECC = "ECC"
    BOOK_SNG = "SNG"
    BOOK_ISA = "ISA"
    BOOK_JER = "JER"
    BOOK_LAM = "LAM"
    BOOK_EZK = "EZK"
    BOOK_DAN = "DAN"
    BOOK_HOS = "HOS"
    BOOK_JOL = "JOL"
    BOOK_AMO = "AMO"
    BOOK_OBA = "OBA"
    BOOK_JON = "JON"
    BOOK_MIC = "MIC"
    BOOK_NAM = "NAM"
    BOOK_HAB = "HAB"
    BOOK_ZEP = "ZEP"
    BOOK_HAG = "HAG"
    BOOK_ZEC = "ZEC"
    BOOK_MAL = "MAL"
    BOOK_MAT = "MAT"
    BOOK_MRK = "MRK"
    BOOK_LUK = "LUK"
    BOOK_JHN = "JHN"
    BOOK_ACT = "ACT"
    BOOK_ROM = "ROM"
    BOOK_1CO = "1CO"
    BOOK_2CO = "2CO"
    BOOK_GAL = "GAL"
    BOOK_EPH = "EPH"
    BOOK_PHP = "PHP"
    BOOK_COL = "COL"
    BOOK_1TH = "1TH"
    BOOK_2TH = "2TH"
    BOOK_1TI = "1TI"
    BOOK_2TI = "2TI"
    BOOK_TIT = "TIT"
    BOOK_PHM = "PHM"
    BOOK_HEB = "HEB"
    BOOK_JAS = "JAS"
    BOOK_1PE = "1PE"
    BOOK_2PE = "2PE"
    BOOK_1JN = "1JN"
    BOOK_2JN = "2JN"
    BOOK_3JN = "3JN"
    BOOK_JUD = "JUD"
    BOOK_REV = "REV"
