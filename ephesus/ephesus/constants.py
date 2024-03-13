"""
Constants used in this application
"""
from enum import Enum, unique, EnumMeta
from collections import namedtuple
from dataclasses import dataclass, field

from functools import partial

from datetime import datetime, timezone

from .exceptions import (
    InputError,
)

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


@dataclass
class ProjectMetadata:
    """Class for storing project metadata in DB as JSON"""

    # Using JSON naming convention
    uploadTime: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).strftime(
            DATETIME_TZ_FORMAT_STRING
        )
    )

    def get_upload_time(self) -> datetime:
        return datetime.strptime(self.uploadTime, DATETIME_TZ_FORMAT_STRING)


class EphesusEnvType(Enum):
    """Ephesus app environment types"""

    DEVELOPMENT = 1
    STAGING = 2
    PRODUCTION = 3


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


# The String to call the 'latest' version of the project
LATEST_PROJECT_VERSION_NAME: str = "latest"

# The name of the directory where the
# file(s) uploaded by the user are stored as-is
PROJECT_UPLOAD_DIR_NAME: str = "upload"

# The name of the directory where the
# uploaded compressed files are extracted to.
PROJECT_CLEAN_DIR_NAME: str = "clean"

# The name of the versification file
# used for the project. It's the same
# name across all projects.
PROJECT_VREF_FILE_NAME: str = "vref.txt"

# The timezone-aware datetime format string
# used internally in this application
DATETIME_TZ_FORMAT_STRING = "%Y-%m-%d %H:%M:%S %z"

# The timezone-aware datetime format
# string used for UI purposes. Assumes
# the the time output is in UTC.
DATETIME_UTC_UI_FORMAT_STRING = "%B %d, %Y at %H:%M UTC"

# The template for downloaded file names
WILDEBEEST_DOWNLOAD_FILENAME = "wildebeest-report-{name}.txt"

# The symbol that marks verse ranges
# in the BibleNLP format.
BIBLENLP_RANGE_SYMBOL = "<range>"

## Patterns
# Patterns for USFM files.
# Not regex but usable in Path.glob()
USFM_FILE_PATTERNS: list[str] = ["*.[sS][fF][mM]", "*.[uU][sS][fF][mM]"]

# Pattern for .zip files.
# Not regex but usable in Path.glob()
ZIP_FILE_PATTERN: str = "*.[zZ][iI][pP]"


# Enum of all global state keys
@unique
class GlobalStates(Enum, metaclass=MyEnumMeta):
    """All global state keys for the app"""
    VREF_INDEX = "vref_index"

@unique
class BookCodes(Enum, metaclass=MyEnumMeta):
    """
    All Bible books 3-letter codes.
    Includes stuff outside of the protestant Bible.
    Taken from https://docs.usfm.bible/usfm-usx-docs/latest/para/identification/books.html
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
    BOOK_TOB = "TOB"
    BOOK_JDT = "JDT"
    BOOK_ESG = "ESG"
    BOOK_WIS = "WIS"
    BOOK_SIR = "SIR"
    BOOK_BAR = "BAR"
    BOOK_LJE = "LJE"
    BOOK_S3Y = "S3Y"
    BOOK_SUS = "SUS"
    BOOK_BEL = "BEL"
    BOOK_1MA = "1MA"
    BOOK_2MA = "2MA"
    BOOK_3MA = "3MA"
    BOOK_4MA = "4MA"
    BOOK_1ES = "1ES"
    BOOK_2ES = "2ES"
    BOOK_MAN = "MAN"
    BOOK_PS2 = "PS2"
    BOOK_ODA = "ODA"
    BOOK_PSS = "PSS"
    BOOK_EZA = "EZA"
    BOOK_5EZ = "5EZ"
    BOOK_6EZ = "6EZ"
    BOOK_DAG = "DAG"
    BOOK_PS3 = "PS3"
    BOOK_2BA = "2BA"
    BOOK_LBA = "LBA"
    BOOK_JUB = "JUB"
    BOOK_ENO = "ENO"
    BOOK_1MQ = "1MQ"
    BOOK_2MQ = "2MQ"
    BOOK_3MQ = "3MQ"
    BOOK_REP = "REP"
    BOOK_4BA = "4BA"
    BOOK_LAO = "LAO"


@dataclass
class BibleReference:
    """Class for holding a Biblical reference (BCV)"""

    book: BookCodes
    chapter: str = None
    verse: str = None

    @classmethod
    def from_string(cls, ref: str):
        """Initialize an object a Bible reference string"""
        if not len or len(ref) < 3:
            raise InputError(
                "Invalid Bible reference string. It must be of the form BOOK Chapter:Verse"
            )

        book: str
        cv: str | None
        book, cv = ref.split()
        if book.upper() not in BookCodes:
            raise InputError(
                "Invalid Bible reference string. No matching Book Code found."
            )
        if not cv:
            return cls(book=book)

        if ":" in cv:
            return cls(book=book, chapter=cv.split(":")[0], verse=cv.split(":")[1])

        return cls(book=book, chapter=cv)

    def get_formatted_reference(self) -> str:
        if chapter and verse:
            return f"{book} {chapter}:{verse}"

        if chapter:
            return f"{book} {chapter}"

        return book
