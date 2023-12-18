"""
Main entry point for the Ephesus application
"""
# Imports
import logging
from logging.config import dictConfig

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .home import routes as home_routes
from .wildebeest import routes as wildebeest_routes
from .database.setup import SessionLocal, engine, Base

from .config import LogConfig, get_ephesus_settings
from .constants import EphesusEnvType

# Get app settings
ephesus_settings = get_ephesus_settings()

# Get and set logger
dictConfig(LogConfig().dict())
_LOGGER = logging.getLogger(__name__)

# Create DB instance
Base.metadata.create_all(bind=engine)

# Create and configure app instance
app = FastAPI()
app.mount("/static", StaticFiles(packages=[("ephesus.home", "static")]), name="static")

# Home routes
app.include_router(home_routes.ui_router)
app.include_router(home_routes.api_router)

# Wildebeest routes
app.include_router(wildebeest_routes.api_router)
app.include_router(wildebeest_routes.ui_router)


# Add user auth headers for running app only in development mode.
# Usually, these headers are supplied by the auth proxy server.
if ephesus_settings.ephesus_env.lower() == EphesusEnvType.DEVELOPMENT.name.lower():

    @app.middleware("http")
    async def add_user_headers(request: Request, call_next):
        # Add user headers to request for running in dev mode
        headers = dict(request.scope["headers"])
        headers[b"x-forwarded-user"] = b"bob"
        headers[b"x_forwarded_email"] = b"bob@greekroom.org"
        headers[b"x_forwarded_preferred_username"] = b"bob"

        request.scope["headers"] = [(k, v) for k, v in headers.items()]

        return await call_next(request)
