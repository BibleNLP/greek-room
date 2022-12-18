"""
Utilities in service of the word checker prototype
"""

# Core python imports
import abc
import json
import logging
from pathlib import Path
from collections import defaultdict

# This project
from web.ephesus.constants import BookCodes
from web.ephesus.exceptions import InternalError

# Third party
from usfm_grammar import USFMParser, Filter

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
            if len(list(input_directory_path.glob("**/*.tsv"))) == 0:
                _LOGGER.info(f"Could not find any TSV files in {self.input_directory}")
                return
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

    def bcvv_iterator(self):
        """A book-chapter-versenumber-verse iterator"""
        for book in self.data:
            for chapter in self.data[book]:
                for verse in self.data[book][chapter]:
                    yield book, chapter, verse, self.data[book][chapter][verse]


class USFMDataExtractor(DataExtractor):
    """
    Process Scriptural data in USFM format
    """

    def __init__(self, input_filepath):
        """Initialize the extractor"""
        _LOGGER.debug("Initializing USFMDataExtractor")
        self.input_filepath = input_filepath
        self.data = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))

        self.extract_data()

        _LOGGER.debug("Finished initializing USFMDataExtractor")

    def extract_data(self):
        """
        Extract the scripture content from a USFM file
        and store them in a dict for easy access.
        """
        _LOGGER.debug("Starting work to extract data from USFM file")
        try:
            file_content = open(
                self.input_filepath, encoding="utf-8", errors="surrogateescape"
            ).read()
            usfm_parser = USFMParser(file_content)

            # Get verses list from USFM
            verses = usfm_parser.to_list([Filter.SCRIPTURE_TEXT])
            _LOGGER.info(verses)

            for entry in verses[1:]:
                self.data[entry[0]][entry[1]][entry[2]] = entry[3].strip('"').strip()

            _LOGGER.debug("Finished work to extract data from USFM file")
        except Exception as e:
            _LOGGER.exception("Could not extract USFM data", e)

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

    def bcvv_iterator(self):
        """A book-chapter-versenumber-verse iterator"""
        for book in self.data:
            for chapter in self.data[book]:
                for verse in self.data[book][chapter]:
                    yield book, chapter, verse, self.data[book][chapter][verse]


class JSONDataExtractor(DataExtractor):
    """
    Process Scriptural data in JSON format
    """

    def __init__(self, input_directory):
        """Initialize the extractor with the input directory"""
        self.input_directory = input_directory
        self.data = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))

        self.extract_data()

    def extract_data(self):
        """
        Extract the scripture content from .json files and
        store them in a dict for easy access.
        """
        try:
            input_directory_path = Path(self.input_directory)
            if len(list(input_directory_path.glob("**/*.json"))) == 0:
                _LOGGER.info(f"Could not find any JSON files in {self.input_directory}")
                return
            for json_file in input_directory_path.glob("**/*.json"):
                with json_file.open() as json_filehandler:
                    self.data = {**self.data, **json.load(json_filehandler)}

        except Exception as e:
            _LOGGER.exception("Could not extract JSON data", e)

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

    def bcvv_iterator(self):
        """A book-chapter-versenumber-verse iterator"""
        for book in self.data:
            for chapter in self.data[book]:
                for verse in self.data[book][chapter]:
                    yield book, chapter, verse, self.data[book][chapter][verse]


def parse_input(filepath, resource_id):
    """Parse and store the uploaded input file as JSON"""
    if filepath.suffix.lower() in [".sfm", ".usfm"]:
        parser = USFMDataExtractor(str(filepath))

    with open(f"{filepath.parent / resource_id}.json", "w") as json_file:
        json.dump(parser.data, json_file)


def update_file_content(json_content, filepath):
    """Write updated JSON content back to file"""
    if not json_content or len(json_content) == 0:
        raise InternalError()

    with open(filepath, "w") as json_file:
        json.dump(json_content, json_file)
