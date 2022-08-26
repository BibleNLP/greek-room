"""
For words found in the data, find spelling errors
and suggest list of possible corrections
"""

# Core Python imports
from dataclasses import dataclass, field
from pathlib import Path
import logging

# 3rd party imports
import flask


_LOGGER = logging.getLogger(__name__)


@dataclass
class SpellSuggestion:
    """
    Class for keeping track of a single spelling
    error and the suggested corrections
    """

    # The token (1 or more words) that is suspect
    error_token: str = None

    # The list of suggestions for corrections.
    # This is tuple of (token, probability)
    # ordered descending by probability.
    suggestions: list[tuple] = field(default_factory=list)


class SpellChecker:
    """
    Class for spell checking input data
    """

    def __init__(self, lang_code):
        self.lang_code = lang_code

    def get_spell_suggestions(self):
        return [
            SpellSuggestion(
                error_token="sarvant", suggestions=[("servant", 0.83), ("savant", 0.70)]
            ),
            SpellSuggestion(
                error_token="goodliness",
                suggestions=[("godliness", 0.91), ("good lines", 0.15)],
            ),
        ]

    def analyze_text(self, extracted_data, resource_id=None):
        """
        Tokenize and calculate frequencies
        of the tokens in the text.
        Meant to be called the first time
        when loading a new text.
        """
        analysis_filepath = Path(
            f'{flask.current_app.config["DATA_PATH"]}/analysis/{self.lang_code}.json'
        )

        try:
            # If no resource_id given, use the
            # name of the directory with the files in it.
            if not resource_id:
                resource_id = Path(extracted_data.input_directory).name

            analysis_data = {}
            with analysis_filepath.open() as analysis_file:
                try:
                    analysis_data = json.load(analysis_file)

                except json.JSONDecodeError as json_error:
                    _LOGGER.debug("Unable to read analysis file. ", json_error)

            if (
                not "sources" in analysis_data
                or not resource_id in analysis_data["sources"]
            ):
                sources = defaultdict(lambda: defaultdict(list))
            else:
                sources = analysis_data["sources"][resource_id]

            for book, chapter, verse_number, verse in extracted_data.bcvv_iterator():
                if verse_number in sources.get(book, {}).get(chapter, []):
                    continue

        except Exception as e:
            _LOGGER.exception("Unable to run analysis. ", e)
