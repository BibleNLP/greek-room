import logging
import secrets
import shutil
import traceback
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
    HTTPException,
)

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from babel.dates import format_timedelta

from ..config import get_ephesus_settings
from ..constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_UPLOAD_DIR_NAME,
    PROJECT_CLEAN_DIR_NAME,
)
from ..dependencies import (
    get_db,
)
from ..database import crud, schemas
from ..exceptions import InputError
from ..common.utils import (
    secure_filename,
    parse_files,
)

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


# TODO: check and handle inputs with only whitespace
# TODO: Limit file size at reverse-proxy layer (Traefik/Nginx)
@api_router.post("/users/{username}/projects", status_code=status.HTTP_201_CREATED)
def create_user_project(
    username: str,
    files: list[UploadFile],
    project_name: Annotated[str, Form(min_length=3, max_length=50)],
    lang_code: Annotated[str, Form(min_length=2, max_length=8)],
    db: Session = Depends(get_db),
):
    """Create a user project using uploaded data"""
    # _LOGGER.debug(f"{files}, {project_name}, {lang_code}")

    # Save file in a new randomly named dir
    resource_id: str = secrets.token_urlsafe(6)
    project_path: Path = (
        ephesus_setting.ephesus_projects_dir / resource_id / LATEST_PROJECT_VERSION_NAME
    )

    # Create the project directories.
    # including any missing parents
    (project_path / PROJECT_UPLOAD_DIR_NAME).mkdir(parents=True)
    # (project_path / PROJECT_UPLOADED_DIR_NAME).mkdir(parents=True)

    # Store to the upload dir within the project dir
    for file in files:
        try:
            with (
                project_path
                / PROJECT_UPLOAD_DIR_NAME
                / Path(secure_filename(file.filename))
            ).open("wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            _LOGGER.exception(e)
            # clean-up
            shutil.rmtree((ephesus_setting.ephesus_projects_dir / resource_id))

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error uploading the file(s). Try again.",
            )
        finally:
            # clean-up
            file.file.close()

    # Parse the uploaded files and
    # save them to the clean dir
    try:
        parse_files(
            (project_path / PROJECT_UPLOAD_DIR_NAME),
            (project_path / PROJECT_CLEAN_DIR_NAME),
            resource_id,
        )
    except InputError as ine:
        # clean-up
        shutil.rmtree((ephesus_setting.ephesus_projects_dir / resource_id))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ine),
        )

    return {
        "message": f"Successfuly uploaded {len([file.filename for file in files])} file(s)."
    }

    # # Parse uploaded file
    #             parse_uploaded_files(parsed_filepath, resource_id)

    #             # Add project to DB and connect with user
    #             project_db_instance = Project(
    #                 resource_id=resource_id,
    #                 name=project_name,
    #                 lang_code=lang_code,
    #             )
    #             project_access = ProjectAccess(
    #                 project=project_db_instance,
    #                 user=current_user,
    #                 access_type=ProjectAccessType.OWNER.name,
    #             )
    #             project_db_instance.users.append(project_access)
    #             db.session.add(project_db_instance)

    return {"hello": "world"}


#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter(
    tags=["UI"],
)


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request, db: Session = Depends(get_db)):

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
