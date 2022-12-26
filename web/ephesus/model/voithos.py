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

    ACCEPT = 1
    REJECT = 2
    HIDE = 3


class SuggestionSource(enum.Enum):
    """The source for the suggestion"""

    HUMAN = 1
    AI = 2


class FlaggedTokens(db.Model):
    """Model to hold the tokens that maybe incorrect and should be flagged"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    tokens = db.Column(db.Text)


class Suggestions(db.Model):
    """Model to hold suggestions for the FlaggedTokens"""

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String(10))
    suggestion = db.Column(db.Text)
    suggestion_type = db.Column(Enum(SuggestionType))
    confidence = db.Column(db.Float)
    user_decision = db.Column(Enum(UserDecision))
    suggestion_source = db.Column(Enum(SuggestionSource))


# Join table for NxN relationship between
# FlaggedTokens and Suggestions tables
association_table = db.Table(
    "token_suggestions_association",
    db.Column("flagged_tokens_id", db.ForeignKey(FlaggedTokens.id), primary_key=True),
    db.Column("suggestion_id", db.ForeignKey(Suggestions.id), primary_key=True),
)
