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
        "suggestion": {
            "lang_code": "eng",
            "suggestion": "confident",
            "suggestion_type": SuggestionType.SPELL,
            "confidence": 0.7,
            "user_decision": UserDecision.UNDECIDED,
            "suggestion_source": SuggestionSource.AI,
        },
    }
]

app = ephesus_app.create_app()

with app.app_context():
    for item in seed_data:
        flaggedTokens = FlaggedTokens(**item["flaggedTokens"])
        suggestions = Suggestions(**item["suggestion"])
        flaggedTokens.suggestions.append(suggestions)

        db.session.add(flaggedTokens)
        db.session.add(suggestions)

    db.session.commit()
