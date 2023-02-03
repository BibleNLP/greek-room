"""Standalone script to seed data into the Voithos model"""
## Imports
# from this project
import web.ephesus.app as ephesus_app
from web.ephesus.extensions import db
from web.ephesus.model.voithos import (
    FlaggedTokens,
    Vocabulary,
    TokenSuggestions,
    SuggestionType,
    UserDecisionType,
    SuggestionSourceType,
)

seed_data = [
    {
        "flagged_tokens": [{"lang_code": "eng", "token": "confidint"}],
        "vocabulary": [
            {
                "lang_code": "eng",
                "entry": "confident",
            },
            {"lang_code": "eng", "entry": "confidante"},
        ],
        "token_suggestions": [
            {
                "mapping": {"flagged_token_idx": 0, "vocabulary_idx": 0},
                "association_data": {
                    "suggestion_type": SuggestionType.SPELLING,
                    "confidence": 0.7,
                    "user_decision_type": UserDecisionType.UNDECIDED,
                    "suggestion_source_type": SuggestionSourceType.AI,
                },
            },
            {
                "mapping": {"flagged_token_idx": 0, "vocabulary_idx": 1},
                "association_data": {
                    "suggestion_type": SuggestionType.SPELLING,
                    "confidence": 0.3,
                    "user_decision_type": UserDecisionType.UNDECIDED,
                    "suggestion_source_type": SuggestionSourceType.AI,
                },
            },
        ],
    }
]

app = ephesus_app.create_app()

with app.app_context():
    for item in seed_data:
        flagged_tokens = []
        vocabulary = []

        # Create FlaggedTokens
        for flagged_token in item["flagged_tokens"]:
            flagged_tokens.append(FlaggedTokens(**flagged_token))

        # Create Vocabulary
        for vocabulary_entry in item["vocabulary"]:
            vocabulary.append(Vocabulary(**vocabulary_entry))

        # Create TokenSuggestions
        for suggestion in item["token_suggestions"]:
            token_suggestion_data = {
                **{
                    "flagged_token": flagged_tokens[
                        suggestion["mapping"]["flagged_token_idx"]
                    ],
                    "suggestion": vocabulary[suggestion["mapping"]["vocabulary_idx"]],
                },
                **suggestion["association_data"],
            }

            token_suggestion = TokenSuggestions(**token_suggestion_data)

            # Add to DB
            db.session.add(token_suggestion)

    # Commit
    db.session.commit()
