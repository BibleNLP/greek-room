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

# Import from this project
from web.ephesus.extensions import db
from web.ephesus.model.voithos import FlaggedTokens, Suggestions

_LOGGER = logging.getLogger(__name__)


def get_suggestions_for_resource(resource_id, book, chapter, verse):
    """Query DB to get all relevant suggestions for a specific `resource_id`"""
    flagged_tokens = db.session.scalars(db.select(FlaggedTokens)).all()
    suggestions = []
    for flagged_token_row in flagged_tokens:
        per_token_suggestions = []
        for suggestions_row in flagged_token_row.suggestions:
            per_token_suggestions.append(
                {
                    "suggestion_id": suggestions_row.id,
                    "lang_code": suggestions_row.lang_code,
                    "suggestion": suggestions_row.suggestion,
                    "confidence": suggestions_row.confidence,
                    "suggestion_type": suggestions_row.suggestion_type.name,
                    "user_decision": suggestions_row.user_decision.name,
                    "suggestion_source": suggestions_row.suggestion_source.name,
                }
            )

        suggestions.append(
            {
                "flagged_token_id": flagged_token_row.id,
                "lang_code": flagged_token_row.lang_code,
                "flagged_token": flagged_token_row.token,
                "suggestions": per_token_suggestions,
            }
        )

    return suggestions


@dataclass
class Suggestion:
    """
    Class for keeping track of a single
    flagged token and the suggested corrections/predictions
    """

    # The token (1 or more words) that is suspect
    flagged_token: str = None

    # The list of suggestions for corrections/predictions.
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
