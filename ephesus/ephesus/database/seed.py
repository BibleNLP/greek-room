"""
Provide initial seed data for bootstrapping the app
"""

seed_data = {
    "user": [
        {
            "username": "bob",
        },
        {
            "username": "sam",
        },
    ],
    "project": [
        {
            "resource_id": "resource1",
            "name": "Hindi NT",
            "lang_code": "hin",
            "status": "ACTIVE",
        },
        {
            "resource_id": "zxcv5678",
            "name": "German NT",
            "lang_code": "de",
            "status": "ACTIVE",
        },
    ],
    "project_access": [
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
