"""Model for the Voithos (word/spell checker) blueprint"""
## Imports
# Core python imports
import enum

# 3rd party imports
from sqlalchemy import Enum

# from this project
from web.ephesus.extensions import db

# Enums
class SuggestionType(enum.Enum):
    """Different types of Suggestions possible"""

    SPELL = 1
    CONSISTENCY = 2
    PREDICTION = 3


class UserDecision(enum.Enum):
    """Choices made by the user on suggestions"""

    UNDECIDED = 1
    ACCEPT = 2
    REJECT = 3
    HIDE = 4


class SuggestionSource(enum.Enum):
    """The source for the suggestion"""

    HUMAN = 1
    AI = 2


class FlaggedTokens(db.Model):
    """Model to hold the tokens that maybe incorrect and should be flagged"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    token = db.Column(db.Text)
    suggestions = db.relationship(
        "Suggestions",
        secondary=lambda: association_table,
        back_populates="flagged_tokens",
    )

    def __init__(self, lang_code, token):
        self.lang_code = lang_code
        self.token = token


class Suggestions(db.Model):
    """Model to hold suggestions for the FlaggedTokens"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    suggestion = db.Column(db.Text)
    suggestion_type = db.Column(Enum(SuggestionType))
    confidence = db.Column(db.Float)
    user_decision = db.Column(Enum(UserDecision))
    suggestion_source = db.Column(Enum(SuggestionSource))
    flagged_tokens = db.relationship(
        "FlaggedTokens",
        secondary=lambda: association_table,
        back_populates="suggestions",
    )

    def __init__(
        self,
        lang_code,
        suggestion,
        suggestion_type=SuggestionType.SPELL,
        confidence=0.0,
        user_decision=UserDecision.UNDECIDED,
        suggestion_source=SuggestionSource.AI,
    ):
        self.lang_code = lang_code
        self.suggestion = suggestion
        self.suggestion_type = suggestion_type
        self.confidence = confidence
        self.user_decision = user_decision
        self.suggestion_source = suggestion_source


# Join table for NxN relationship between
# FlaggedTokens and Suggestions tables
association_table = db.Table(
    "token_suggestions_association",
    db.Column("flagged_tokens_id", db.ForeignKey(FlaggedTokens.id), primary_key=True),
    db.Column("suggestion_id", db.ForeignKey(Suggestions.id), primary_key=True),
)
