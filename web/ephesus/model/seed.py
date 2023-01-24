"""Standalone script to seed data into the Voithos model"""
## Imports
# from this project
import web.ephesus.app as ephesus_app
from web.ephesus.extensions import db
from web.ephesus.model.voithos import (
    FlaggedTokens,
    Suggestions,
    SuggestionType,
    UserDecision,
    SuggestionSource,
)

seed_data = [
    {
        "flaggedTokens": {"lang_code": "eng", "token": "confidint"},
        "suggestions": [
            {
                "lang_code": "eng",
                "suggestion": "confident",
                "suggestion_type": SuggestionType.SPELLING,
                "confidence": 0.7,
                "user_decision": UserDecision.UNDECIDED,
                "suggestion_source": SuggestionSource.AI,
            },
            {
                "lang_code": "eng",
                "suggestion": "confidante",
                "suggestion_type": SuggestionType.SPELLING,
                "confidence": 0.3,
                "user_decision": UserDecision.UNDECIDED,
                "suggestion_source": SuggestionSource.AI,
            },
        ],
    }
]

app = ephesus_app.create_app()

with app.app_context():
    for item in seed_data:
        flaggedTokens = FlaggedTokens(**item["flaggedTokens"])
        # suggestions = Suggestions(**item["suggestion"])
        for suggestion_item in item["suggestions"]:
            suggestion = Suggestions(**suggestion_item)
            flaggedTokens.suggestions.append(suggestion)

            db.session.add(suggestion)
        db.session.add(flaggedTokens)

    db.session.commit()
