"""
Main entry point for the Ephesus application
"""
# Imports
import logging
from logging.config import dictConfig

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from .dependencies import get_query_token, get_token_header
from .wildebeest import routes as wildebeest_routes
from .home import routes as home_routes
from .routers import items
from .database.setup import SessionLocal, engine, Base

from .config import LogConfig

# Get and set logger
_LOGGER = logging.getLogger(__name__)
dictConfig(LogConfig().dict())

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

# @app.get("/")
# async def root():
#     return {"message": "Hello Bigger Applications!"}
