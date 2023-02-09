"""
Model for the Voithos (word/spell checker) blueprint
"""

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

    SPELLING = 1
    CONSISTENCY = 2
    PREDICTION = 3


class UserDecisionType(enum.Enum):
    """Choices made by the user on suggestions"""

    UNDECIDED = 1
    ACCEPT = 2
    REJECT = 3
    HIDE = 4


class SuggestionSourceType(enum.Enum):
    """The source for the suggestion"""

    HUMAN = 1
    AI = 2


class FlaggedTokens(db.Model):
    """Model to hold the tokens that maybe incorrect and should be flagged"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    token = db.Column(db.Text)
    suggestions = db.relationship(
        "TokenSuggestions",
        back_populates="flagged_token",
    )

    def __init__(self, lang_code, token):
        self.lang_code = lang_code
        self.token = token


class Vocabulary(db.Model):
    """Model to hold valid words/phrases in multiple languages"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    entry = db.Column(db.Text)
    flagged_tokens = db.relationship(
        "TokenSuggestions",
        back_populates="suggestion",
    )

    def __init__(self, lang_code, entry):
        self.lang_code = lang_code
        self.entry = entry


# Join table for NxN relationship between
# FlaggedTokens and Vocabulary tables
class TokenSuggestions(db.Model):
    """Model to connect FlaggedTokens with Vocabulary with metadata"""

    id = db.Column(db.Integer, primary_key=True)
    flagged_tokens_id = db.Column(db.Integer, db.ForeignKey(FlaggedTokens.id))
    vocabulary_id = db.Column(db.Integer, db.ForeignKey(Vocabulary.id))
    user_decision_type = db.Column(Enum(UserDecisionType))
    suggestion_type = db.Column(Enum(SuggestionType))
    confidence = db.Column(db.Float, default=0.0)
    suggestion_source_type = db.Column(Enum(SuggestionSourceType))

    flagged_token = db.relationship("FlaggedTokens", back_populates="suggestions")
    suggestion = db.relationship("Vocabulary", back_populates="flagged_tokens")

    def __init__(
        self,
        flagged_token,
        suggestion,
        user_decision_type=UserDecisionType.UNDECIDED,
        suggestion_type=SuggestionType.SPELLING,
        confidence=0.0,
        suggestion_source_type=SuggestionSourceType.AI,
    ):
        self.flagged_token = flagged_token
        self.suggestion = suggestion
        self.user_decision_type = user_decision_type
        self.suggestion_type = suggestion_type
        self.confidence = confidence
        self.suggestion_source_type = suggestion_source_type
