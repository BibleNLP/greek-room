"""
Main entry point for the Ephesus application
"""
# Imports
import logging
from logging.config import dictConfig

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from sqlalchemy.event import listen as sqlalchemy_listen

from .auth import routes as auth_routes
from .home import routes as home_routes
from .wildebeest import routes as wildebeest_routes
from .spell import routes as spell_routes
from .database.setup import SessionLocal, engine, Base

from .config import (
    LogConfig,
    get_ephesus_settings,
    lifespan,
)
from .constants import EphesusEnvType

# Get app settings
ephesus_settings = get_ephesus_settings()

# Get and set logger
dictConfig(LogConfig().dict())
_LOGGER = logging.getLogger(__name__)

# Create DB instance
Base.metadata.create_all(bind=engine)

# Create and configure app instance
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(packages=[("ephesus.home", "static")]), name="static")
app.mount("/static-spell", StaticFiles(packages=[("ephesus.spell", "static")]), name="static-spell")

# Auth routes
app.include_router(auth_routes.api_router)

# Home routes
app.include_router(home_routes.ui_router)
app.include_router(home_routes.api_router)

# Wildebeest routes
app.include_router(wildebeest_routes.api_router)
app.include_router(wildebeest_routes.ui_router)

# Spell checker routes
app.include_router(spell_routes.ui_router)

# Usually, these headers are supplied by the auth proxy server.
if ephesus_settings.ephesus_env.lower() == EphesusEnvType.DEVELOPMENT.name.lower():
    _LOGGER.debug("**App running in development environment**")

    @app.middleware("http")
    async def add_user_headers(request: Request, call_next):
        # Add user headers to request for running in dev mode
        # These headers need to be lowercased to match their
        # internal representation, while injecting.
        headers = dict(request.scope["headers"])
        headers[b"x-forwarded-user"] = b"bob"
        headers[b"x-forwarded-email"] = b"bob@greekroom.org"
        headers[b"x-forwarded-preferred-username"] = b"bob"
        headers[b"x-access-token"] = b"my_development_token"

        request.scope["headers"] = [(k, v) for k, v in headers.items()]

        return await call_next(request)
