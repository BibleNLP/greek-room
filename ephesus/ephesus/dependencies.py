"""
Common dependencies useful for the Ephesus application
"""
import logging

from fastapi.security import OAuth2AuthorizationCodeBearer
from fief_client import FiefAsync
from fief_client.integrations.fastapi import FiefAuth

from .config import get_ephesus_settings
from .database.setup import SessionLocal

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# Get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


API_AUTH = None

# # Auth
# async def create_api_auth_client():
#     """Create an auth client for the app"""

#     fief = FiefAsync(
#         "http://greek-room.localhost:9000/ephesus",
#         ephesus_settings.ephesus_client_id,
#         ephesus_settings.ephesus_client_secret,
#     )

#     # Auth instance for API
#     api_scheme = OAuth2AuthorizationCodeBearer(
#         "http://greek-room.localhost:9000/ephesus/authorize",
#         "http://greek-room.localhost:9000/ephesus/api/token",
#         scopes={"openid": "openid", "offline_access": "offline_access"},
#         auto_error=False,
#     )
#     return FiefAuth(fief, api_scheme)


# def get_api_auth_client():
#     """Create a singleton instance of the client"""
#     global API_AUTH
#     if not API_AUTH:
#         API_AUTH = await create_api_auth_client()

#     return API_AUTH


fief = FiefAsync(
    "https://test-jt756c.fief.dev",
    ephesus_settings.ephesus_client_id,
    ephesus_settings.ephesus_client_secret,
    verify=False,
)

# Auth instance for API
api_scheme = OAuth2AuthorizationCodeBearer(
    "https://test-jt756c.fief.dev/authorize",
    "https://test-jt756c.fief.dev/api/token",
    scopes={"openid": "openid", "offline_access": "offline_access"},
    auto_error=False,
)

api_auth = FiefAuth(fief, api_scheme)
