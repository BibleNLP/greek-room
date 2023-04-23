"""Standalone script to seed data into the Voithos model"""
## Imports
# from this project
import web.ephesus.app as ephesus_app
from web.ephesus.extensions import db
from web.ephesus.model.user import (
    User,
)
from web.ephesus.model.voithos import (
    FlaggedTokens,
    Vocabulary,
    TokenSuggestions,
    SuggestionType,
    UserDecisionType,
    SuggestionSourceType,
)

voithos_seed_data = [
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

user_seed_data = {
    "users": [
        {
            "email": "john@example.com",
            "password": "0b47c69b1033498d5f33f5f7d97bb6a3126134751629f4d0185c115db44c094e",
            "name": "John Doe",
        }
    ]
}

app = ephesus_app.create_app()

with app.app_context():
    # Seed users
    for seed_user in user_seed_data["users"]:
        user = User(**seed_user)
        db.session.add(user)

    # Seed data for spell checking
    for item in voithos_seed_data:
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
