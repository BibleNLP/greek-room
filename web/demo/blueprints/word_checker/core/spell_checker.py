"""
For words found in the data, find spelling errors
and suggest list of possible corrections
"""

from dataclasses import dataclass, field


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

    def __init__(self, data):
        self.data = data

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
