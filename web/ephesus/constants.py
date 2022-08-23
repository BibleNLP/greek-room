"""
Constants used in this application
"""
from enum import Enum, unique, EnumMeta


class MyEnumMeta(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        else:
            return True


@unique
class BookCodes(Enum, metaclass=MyEnumMeta):
    """
    Enum of all Bible books.
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
