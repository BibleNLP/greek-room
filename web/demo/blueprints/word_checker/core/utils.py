"""
Utilities in service of the word checker prototype
"""

from abc import ABCMeta


class DataExtractor(metaclass=ABCMeta):
    """
    Abstract class to work with multiple sources
    of input data.
    """

    @property
    @abstractmethod
    def get_data(self):
        """Get the data as a list of sentences"""
        return None


class TSVDataExtractor(DataExtractor):
    """
    Process Scriptural data in TSV format
    """

    def __init__(self):


    def get_data(self):
        pass
