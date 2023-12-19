"""
Main entry point for the Ephesus application
"""
# Imports
import logging
from logging.config import dictConfig

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from sqlalchemy.event import listen as sqlalchemy_listen

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
    _LOGGER.debug("**App running in development environment**")

    @app.middleware("http")
    async def add_user_headers(request: Request, call_next):
        # Add user headers to request for running in dev mode
        headers = dict(request.scope["headers"])
        headers[b"x-forwarded-user"] = b"bob"
        headers[b"x_forwarded_email"] = b"bob@greekroom.org"
        headers[b"x_forwarded_preferred_username"] = b"bob"

        request.scope["headers"] = [(k, v) for k, v in headers.items()]

        return await call_next(request)

    # @app.on_event("startup")
    # async def populate_seed_data():
    #     """Setup seed data for development"""
    #     # This is here to avoid circular imports
    #     from .database.models.user_projects import (
    #         User,
    #         Project,
    #         ProjectAccess,
    #     )
    #     from .database.seed import seed_data

    #     # This method receives a table, a connection
    #     # and inserts data to that table.
    #     def seed_table(target, connection, **kw):
    #         tablename = str(target)
    #         if tablename in seed_data and len(seed_data[tablename]) > 0:
    #             connection.execute(target.insert(), seed_data[tablename])

    #     _LOGGER.debug("Populating seed data in app database")
    #     sqlalchemy_listen(User.__table__, "after_create", seed_table)
    #     sqlalchemy_listen(Project.__table__, "after_create", seed_table)
    #     sqlalchemy_listen(ProjectAccess.__table__, "after_create", seed_table)
