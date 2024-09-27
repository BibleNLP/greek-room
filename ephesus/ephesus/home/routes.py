"""
API and UI routes for the home page of the application
"""

import logging
import secrets
import shutil
from pathlib import Path
from typing import Annotated
from datetime import datetime, timezone
from dataclasses import asdict, replace

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
from sqlalchemy.exc import DBAPIError

from babel.dates import format_timedelta

from ..config import get_ephesus_settings
from ..constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_UPLOAD_DIR_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_REFERENCES_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
    DATETIME_TZ_FORMAT_STRING,
    DATETIME_UTC_UI_FORMAT_STRING,
    EphesusEnvType,
    ProjectAccessType,
    ProjectMetadata,
    StaticAnalysisResults,
)
from ..dependencies import (
    get_db,
    get_current_username,
    get_current_user_email,
)
from ..database import crud, schemas
from ..exceptions import InputError, OutputError
from ..common.utils import (
    secure_filename,
    parse_files,
    get_scope_from_vref,
    send_email,
    get_datetime,
    get_static_analysis_results_paths,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# Configure templates
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
## Register custom Jinja2 filters
templates.env.filters["timedeltaformat"] = format_timedelta
templates.env.filters["todatetime"] = get_datetime

##############
# API Routes #
##############

# Create API router instance
api_router = APIRouter(
    prefix="/api/v1",
    tags=["projects"],
)


@api_router.get("/projects", response_model=list[schemas.ProjectListModel] | None)
async def get_user_projects(
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Get the list of projects associated with a user"""
    return crud.get_user_projects(db, current_username)


@api_router.get(
    "/projects/{resource_id}",
    response_model=schemas.ProjectWithAccessModel | None,
)
async def get_user_project(
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Get the details of a specific project that belongs to a user"""
    return crud.get_user_project(db, resource_id, current_username)


# TODO: check and handle inputs with only whitespace
# TODO: Limit file size at reverse-proxy layer (Traefik/Nginx)
@api_router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_user_project(
    files: list[UploadFile],
    project_name: Annotated[str, Form(min_length=3, max_length=100)],
    lang_code: Annotated[str, Form(min_length=2, max_length=10)],
    lang_name: Annotated[str, Form(min_length=2, max_length=70)],
    # This >10k to accommodate for browser inserted newline chars
    notes: Annotated[str, Form(max_length=11000)] = None,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Create a user project using uploaded data"""

    # Save file in a new randomly named dir
    resource_id: str = secrets.token_urlsafe(6)
    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
    )

    # Create the project directories.
    # including any missing parents
    (project_path / PROJECT_UPLOAD_DIR_NAME).mkdir(parents=True)

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
            shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error uploading the file(s). Try again.",
            )
        finally:
            # clean-up
            file.file.close()

    try:
        # Parse the uploaded files and
        # save them to the clean dir
        parse_files(
            (project_path / PROJECT_UPLOAD_DIR_NAME),
            (project_path / PROJECT_CLEAN_DIR_NAME),
            resource_id,
        )

        # Save project to DB
        crud.create_user_project(
            db,
            project_name,
            resource_id,
            lang_code,
            lang_name,
            current_username,
            project_metadata=asdict(ProjectMetadata(notes=notes)),
        )

    except InputError as ine:
        _LOGGER.exception(ine)

        # clean-up
        shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"There was an error creating the project. {str(ine)} Try again.",
        )
    except DBAPIError as dbe:
        _LOGGER.exception(dbe)

        # clean-up
        shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error while creating the project. Try again.",
        )

    return {
        "detail": f"Successfully created project using the {len([file.filename for file in files])} uploaded file(s)."
    }


@api_router.delete("/projects/{resource_id}", status_code=status.HTTP_200_OK)
def delete_user_project(
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Delete a user's project identified by `resource_id`"""
    try:
        project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(db, resource_id, current_username)

        # Project not found.
        # Not returning a 404 for security sake.
        if not project_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="There was an error while processing this request. Please try again.",
            )

        # User not project owner
        if project_mapping["ProjectAccess"].access_type != ProjectAccessType.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the rights to delete this project. Contact the project owner.",
            )

        crud.delete_project(db, resource_id)

    except DBAPIError as dbe:
        _LOGGER.exception(dbe)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error while processing this request. Please try again.",
        )

    # Delete files, if DB deletion was successful.
    shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))
    return {"detail": "Successfully deleted project."}


@api_router.get("/projects/{resource_id}/manual-analysis", status_code=status.HTTP_200_OK)
def request_manual_analysis(
    resource_id: str,
    current_user_email: str = Depends(get_current_user_email),
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Send an email requesting manual Greek Room analysis to be run on the `resource_id`"""

    try:
        # Get the user-project details
        project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(db, resource_id, current_username)

        # Project not found.
        # Not returning a 404 for security sake.
        if not project_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="There was an error while processing this request. Please try again.",
            )

        # User not project owner
        if project_mapping["ProjectAccess"].access_type != ProjectAccessType.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions for this project. Contact the project owner.",
            )

        # Create message body
        body = f"""Subject: Greek Room Analysis Request

Dear Greek Room Architects,
I kindly request you to run the Greek Room analysis for my project:

Name: {project_mapping['Project'].name}
ID: {resource_id}/{LATEST_PROJECT_VERSION_NAME}
Language Code: {project_mapping['Project'].lang_code}
Language Name: {project_mapping['Project'].lang_name if project_mapping['Project'].lang_name else ''}
Request Datetime: {datetime.now(tz=timezone.utc).strftime(DATETIME_UTC_UI_FORMAT_STRING)}

Sincerely,
{current_username}
{current_user_email}

PS: Please consider automating the Greek Room analysis steps.
"""
        # Send the email message
        # only if in production
        if ephesus_settings.ephesus_env.lower() == EphesusEnvType.DEVELOPMENT.name.lower():
            _LOGGER.debug(body)
        else:
            send_email(from_addr=ephesus_settings.ephesus_support_email,
                       to_addr=ephesus_settings.ephesus_support_email,
                       body=body)

        # Update project metadata in the DB
        crud.set_user_project_metadata(db, resource_id, replace(crud.get_user_project_metadata(db, resource_id),
                manualAnalysisRequestTime=datetime.now(tz=timezone.utc).strftime(
            DATETIME_TZ_FORMAT_STRING
        )))

    except OutputError as ote:
        _LOGGER.exception(ote)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"There was an error processing your request. Please try again.",
        )
    except DBAPIError as dbe:
        _LOGGER.exception(dbe)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error while processing this request. Please try again.",
        )


@api_router.post("/projects/{project_resource_id}/reference", status_code=status.HTTP_201_CREATED)
def create_project_reference(
    project_resource_id: str,
    files: list[UploadFile],
    reference_name: Annotated[str, Form(min_length=3, max_length=100)],
    lang_code: Annotated[str, Form(min_length=2, max_length=10)],
    lang_name: Annotated[str, Form(min_length=2, max_length=70)],
    # This >10k to accommodate for browser inserted newline chars
    notes: Annotated[str, Form(max_length=11000)] = None,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Create a reference translation project"""

    # Save file in a new randomly named dir
    # Create a new `resource_id` for the reference
    resource_id: str = secrets.token_urlsafe(6)
    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / project_resource_id
        / PROJECT_REFERENCES_DIR_NAME
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
    )

    # Create the project directories.
    # including any missing parents
    (project_path / PROJECT_UPLOAD_DIR_NAME).mkdir(parents=True)

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
            shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="There was an error uploading the file(s). Try again.",
            )
        finally:
            # clean-up
            file.file.close()

    try:
        # Parse the uploaded files and
        # save them to the clean dir
        parse_files(
            (project_path / PROJECT_UPLOAD_DIR_NAME),
            (project_path / PROJECT_CLEAN_DIR_NAME),
            resource_id,
        )

        # Save project to DB
        crud.create_project_reference(
            db,
            reference_name,
            resource_id,
            lang_code,
            lang_name,
            project_resource_id=project_resource_id,
            reference_metadata=asdict(ProjectMetadata(notes=notes))
        )

    except InputError as ine:
        _LOGGER.exception(ine)

        # clean-up
        shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"There was an error creating the project. {str(ine)} Try again.",
        )
    except DBAPIError as dbe:
        _LOGGER.exception(dbe)

        # clean-up
        shutil.rmtree((ephesus_settings.ephesus_projects_dir / resource_id))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error while creating the project. Try again.",
        )

    return {
        "detail": f"Successfully created project reference using the {len([file.filename for file in files])} uploaded file(s)."
    }

#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter(
    tags=["ui"],
)


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(
    request: Request,
    db: Session = Depends(get_db),
    current_username: str = Depends(get_current_username),
):

    projects = crud.get_user_projects(db, current_username)

    # On first time login
    # create projects dirs
    # if not ephesus_settings.ephesus_projects_dir.exists():
    #     ephesus_settings.ephesus_projects_dir.mkdir(parents=True)

    return templates.TemplateResponse(
        "home/index.html",
        {
            "request": request,
            "projects": projects,
            "current_username": current_username,
        },
    )


@ui_router.get("/projects/{resource_id}/overview", response_class=HTMLResponse)
async def get_project_overview(
    resource_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_username: str = Depends(get_current_username),
):
    """Get the basic overview of `resource_id` project"""

    project = crud.get_user_project(db, resource_id, current_username)

    static_analysis_results_paths: StaticAnalysisResults = get_static_analysis_results_paths(resource_id, current_username)

    return templates.TemplateResponse(
        "home/project_overview.fragment",
        {
            "request": request,
            "project": project,
            "project_scope": get_scope_from_vref(
                Path(
                    ephesus_settings.ephesus_projects_dir
                    / resource_id
                    / LATEST_PROJECT_VERSION_NAME
                    / PROJECT_CLEAN_DIR_NAME
                    / PROJECT_VREF_FILE_NAME
                )
            ),
            "current_datetime": datetime.now(timezone.utc),
            "DATETIME_UTC_UI_FORMAT_STRING": DATETIME_UTC_UI_FORMAT_STRING,
            "static_analysis_results_paths": static_analysis_results_paths,
        },
    )
