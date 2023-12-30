"""
API routes for authenticanting the application.

The current setup assumes that all authentication flows
are external to the this codebase. This means that any
request reaching this this app is assumed to be authenticated
and thus has the prerequisite headers to get relevant
user information.
"""

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Request,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)


##############
# API Routes #
##############

# Create API router instance
api_router = APIRouter(
    prefix="/api/v1",
    tags=["auth"],
)


@api_router.get("/token")
async def get_access_token(request: Request) -> dict[str, str]:
    """Get authentication token from the headers"""
    return {"accessToken": request.headers.get("x-access-token")}
