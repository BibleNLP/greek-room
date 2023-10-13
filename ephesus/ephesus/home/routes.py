import logging
from pathlib import Path
from typing import Annotated
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,
    status,
)

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
    """Get the list of projects associated with a user"""
    return crud.get_user_projects(db, username)


@api_router.get(
    "/users/{username}/projects/{resource_id}",
    response_model=schemas.ProjectWithAccessModel | None,
)
async def get_user_project(
    resource_id: str, username: str = "bob", db: Session = Depends(get_db)
):
    """Get the details of a specific project that belongs to a user"""
    return crud.get_user_project(db, resource_id, username)


@api_router.post("/users/{username}/projects", status_code=status.HTTP_201_CREATED)
async def create_user_project(
    username: str,
    files: list[UploadFile],
    project_name: Annotated[str, Form(min_length=3, max_length=50)],
    lang_code: Annotated[str, Form(min_length=2, max_length=8)],
    db: Session = Depends(get_db),
):
    """Create a user project using uploaded data"""

    return {"hello": "world"}


# My favorite project name

#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter(
    tags=["UI"],
)


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


@ui_router.get("/projects/{resource_id}/overview", response_class=HTMLResponse)
async def get_project_overview(
    resource_id: str, request: Request, db: Session = Depends(get_db)
):
    """Get the basic overview of `resource_id` project"""

    project = crud.get_user_project(db, resource_id, "bob")

    return templates.TemplateResponse(
        "home/project_overview.fragment",
        {
            "request": request,
            "project": project,
            "current_datetime": datetime.now(timezone.utc),
        },
    )
