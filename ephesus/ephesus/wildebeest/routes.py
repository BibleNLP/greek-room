"""
API and UI routes for the wildebeest checks
"""

import logging
from pathlib import Path

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

from ..config import get_ephesus_settings
from .core.wildebeest_util import (
    run_wildebeest_analysis,
)
from ..dependencies import (
    get_db,
)
from ..exceptions import InputError
from ..database import crud
from ..database.schemas import ProjectAccessModel

router = APIRouter()

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# Configure templates
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))


# Create API router instance
api_router = APIRouter(
    prefix="/api/v1",
    tags=["wildebeest"],
)


##############
# API Routes #
##############


@api_router.get("/users/{username}/projects/{resource_id}/wildebeest")
async def get_wildebeest_analysis(
    resource_id: str, username: str = "bob", db: Session = Depends(get_db)
) -> dict:
    """Get Wildebeest analysis results"""

    # Check if user has read access on project
    project_mapping = crud.get_user_project(db, resource_id, username)

    # `resource_id` not associated with `username`
    if not project_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )

    try:
        wb_analysis: dict
        ref_id_dict: dict
        wb_analysis, ref_id_dict = run_wildebeest_analysis(resource_id)
        if not wb_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unable to find project contents.",
            )
        return wb_analysis.analysis

    except InputError as ine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )


#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter(
    tags=["UI"],
)


@ui_router.get("/projects/{resource_id}/wildebeest", response_class=HTMLResponse)
async def get_formatted_wildebeest_analysis(
    request: Request, resource_id: str, db: Session = Depends(get_db)
):
    """Get the formatted wildebeest analysis results to show in the UI"""
    # TODO: Get user from session
    username: str = "bob"

    # Check if user has read access on project
    project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(
        db, resource_id, username
    )

    # `resource_id` not associated with `username`
    if not project_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )

    try:
        wb_analysis: dict
        ref_id_dict: dict
        wb_analysis, ref_id_dict = run_wildebeest_analysis(resource_id)
        if not wb_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unable to find project contents.",
            )

        return templates.TemplateResponse(
            "wildebeest/analysis.fragment",
            {
                "request": request,
                "wb_analysis_data": wb_analysis.analysis,
                "ref_id_dict": ref_id_dict,
            },
        )

    except InputError as ine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )
