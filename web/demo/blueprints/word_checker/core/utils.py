"""
Utilities in service of the word checker prototype
"""

# Core python imports
import logging
import abc
from pathlib import Path
from collections import defaultdict

# This project
from web.demo.constants import BookCodes

_LOGGER = logging.getLogger(__name__)


class DataExtractor(metaclass=abc.ABCMeta):
    """
    Abstract class to work with multiple sources
    of input data.
    """

    @abc.abstractmethod
    def extract_data(self):
        """Extract the data into a nested dict structure"""
        return None

    @abc.abstractmethod
    def pretty_print(self):
        """Pretty print to view inside a text area"""
        return None

    def get_book_code_from_filename(self, filename):
        """
        Check if a Bible book code exists
        in the filename and if so, return it
        """
        if not filename or len(filename.strip()) == 0:
            return None

        for book_code in BookCodes:
            if book_code.value in filename.upper():
                return book_code.value

        return None


class TSVDataExtractor(DataExtractor):
    """
    Process Scriptural data in TSV format
    """

    def __init__(self, input_directory):
        """Initialize the extractor with the input directory"""
        self.input_directory = input_directory
        self.data = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))

        self.extract_data()

    def extract_data(self):
        """
        Extract the scripture content from .tsv files and
        store them in a dict for easy access.
        """
        try:
            input_directory_path = Path(self.input_directory)
            for tsv_file in input_directory_path.glob("**/*.tsv"):
                with tsv_file.open() as tsv_filehandler:
                    for idx, line in enumerate(tsv_filehandler):
                        # Assuming first line is header
                        if idx == 0 or len(line.strip()) == 0:
                            continue

                        book_code, chapter, verse, text = line.split(maxsplit=3)
                        self.data[book_code][chapter][verse] = text.strip()

        except Exception as e:
            _LOGGER.exception("Could not extract TSV data", e)

    def pretty_print(self):
        output_lines = []
        for book in self.data:
            for chapter in self.data[book]:
                output_lines.append("")
                for verse in self.data[book][chapter]:
                    output_lines.append(
                        f"{book:<3s} {chapter:>3s} : {verse:<3s} {self.data[book][chapter][verse]}"
                    )

        return "\n".join(output_lines)
