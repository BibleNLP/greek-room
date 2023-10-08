import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from babel.dates import format_timedelta

from ..config import get_ephesus_settings
from ..dependencies import (
    get_db,
)
from ..database import crud, schemas

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_setting = get_ephesus_settings()

# Configure templates
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
## Register custom Jinja2 filters
templates.env.filters["timedeltaformat"] = format_timedelta

##############
# API Routes #
##############

# Create API router instance
api_router = APIRouter(
    prefix="/api/v1",
    tags=["projects"],
)


@api_router.get(
    "/users/{username}/projects", response_model=list[schemas.ProjectListModel] | None
)
async def get_user_projects(username: str = "bob", db: Session = Depends(get_db)):
    return crud.get_user_projects(db, username)


#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter()


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request, db: Session = Depends(get_db)):

    _LOGGER.debug(f"{ephesus_setting.ephesus_projects_dir}")

    projects = crud.get_user_projects(db, "bob")

    # On first time login
    # create projects dirs
    # if not ephesus_setting.ephesus_projects_dir.exists():
    #     ephesus_setting.ephesus_projects_dir.mkdir(parents=True)

    return templates.TemplateResponse(
        "home/index.html",
        {"request": request, "projects": projects},
    )


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request, db: Session = Depends(get_db)):

    _LOGGER.debug(f"{ephesus_setting.ephesus_projects_dir}")

    projects_listing = crud.get_user_projects(db, "bob")

    # On first time login
    # create projects dirs
    # if not ephesus_setting.ephesus_projects_dir.exists():
    #     ephesus_setting.ephesus_projects_dir.mkdir(parents=True)

    return templates.TemplateResponse(
        "home/index.html",
        {"request": request, "projects_listing": projects_listing},
    )


@ui_router.get("/projects/{resource_id}/overview", response_class=HTMLResponse)
async def get_project_overview(
    resource_id: str, request: Request, db: Session = Depends(get_db)
):
    """Get the basic overview of `resource_id` project"""

    project_details = crud.get_user_project_details(db, resource_id, "bob")

    return templates.TemplateResponse(
        "home/project_overview.fragment",
        {
            "request": request,
            "project": project_details,
            "current_datetime": datetime.now(timezone.utc),
        },
    )
