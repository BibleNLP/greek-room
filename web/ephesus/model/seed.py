"""Standalone script to seed data into the Voithos model"""
## Imports
# from this project
import web.ephesus.app as ephesus_app
from web.ephesus.extensions import db
from web.ephesus.model.user import User, Project, ProjectAccess
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

users_seed_data = {
    "users": [
        {
            "email": "bob@email.com",
            "username": "bob",
            "password": "pbkdf2:sha512:210000$UKQsOQDc7Ngj5g1w$6364090ba739122c31f034c5600f67d6ac837058b2282f4a68ac64e171bc0d052767540da7e900af40b8bdbf13dac35bae89fea863b1afdbdefb3034af6fb982",
            "is_email_verified": 1,
            "status": "ACTIVE",
            "roles": "[" "public" "]",
        },
        {
            "email": "sam@email.com",
            "username": "sam",
            "password": "pbkdf2:sha512:210000$jUzijkvcIXcMGJep$303cfec08ac269c91f102c16e580d4dd3798fd0577c23189eb8e729311a7461e483177d0d1c58b8d5b95da8938c48732eb1ec316da88d1f16b7bce3828f09295",
            "is_email_verified": 1,
            "status": "ACTIVE",
            "roles": "[" "public" "," "admin" "]",
        },
    ],
    "projects": [
        {
            "resource_id": "asdf1234",
            "name": "Hindi NT",
            "lang_code": "hin",
            "status": "ACTIVE",
        },
        {
            "resource_id": "zxcv5678",
            "name": "Urdu NT",
            "lang_code": "urd",
            "status": "ACTIVE",
        },
    ],
    "projectAccess": [
        {
            "user_id": 1,
            "project_id": 1,
        },
        {
            "user_id": 1,
            "project_id": 2,
        },
        {"user_id": 2, "project_id": 2, "access_type": "COLLABORATOR"},
    ],
}

app = ephesus_app.create_app()

with app.app_context():
    # Seed User
    for seed_user in users_seed_data["users"]:
        user = User(**seed_user)
        db.session.add(user)

    # Seed Project
    for seed_project in users_seed_data["projects"]:
        project = Project(**seed_project)
        db.session.add(project)

    # Seed ProjectAccess
    for seed_project_access in users_seed_data["projectAccess"]:
        project_access = ProjectAccess(**seed_project_access)
        db.session.add(project_access)

    # # Seed data for spell checking
    # for item in voithos_seed_data:
    #     flagged_tokens = []
    #     vocabulary = []

    #     # Create FlaggedTokens
    #     for flagged_token in item["flagged_tokens"]:
    #         flagged_tokens.append(FlaggedTokens(**flagged_token))

    #     # Create Vocabulary
    #     for vocabulary_entry in item["vocabulary"]:
    #         vocabulary.append(Vocabulary(**vocabulary_entry))

    #     # Create TokenSuggestions
    #     for suggestion in item["token_suggestions"]:
    #         token_suggestion_data = {
    #             **{
    #                 "flagged_token": flagged_tokens[
    #                     suggestion["mapping"]["flagged_token_idx"]
    #                 ],
    #                 "suggestion": vocabulary[suggestion["mapping"]["vocabulary_idx"]],
    #             },
    #             **suggestion["association_data"],
    #         }

    #         token_suggestion = TokenSuggestions(**token_suggestion_data)

    #         # Add to DB
    #         db.session.add(token_suggestion)

    # Commit
    db.session.commit()
