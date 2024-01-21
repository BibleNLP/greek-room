"""
API and UI routes for the wildebeest checks
"""

import logging
from pathlib import Path
import json
from datetime import (
    datetime,
    timezone,
)

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

import redis.asyncio as redis

from ..config import get_ephesus_settings
from ..constants import (
    DATETIME_TZ_FORMAT_STRING,
    ProjectMetadata,
)
from .core.wildebeest_util import (
    run_wildebeest_analysis,
    load_ref_ids,
    is_cache_valid,
)
from ..common.utils import (
    get_datetime,
)
from ..dependencies import (
    get_db,
    get_cache,
    get_current_username,
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


@api_router.get("/projects/{resource_id}/wildebeest")
async def get_wildebeest_analysis(
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
) -> dict:
    """Get Wildebeest analysis results"""

    # Check if user has read access on project
    project_mapping = crud.get_user_project(db, resource_id, current_username)

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
    tags=["ui"],
)


@ui_router.get("/projects/{resource_id}/wildebeest", response_class=HTMLResponse)
async def get_formatted_wildebeest_analysis(
    request: Request,
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
    cache: redis.client.Redis = Depends(get_cache),
):
    """Get the formatted wildebeest analysis results to show in the UI"""
    # Check if user has read access on project
    project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(
        db, resource_id, current_username
    )
    # Get upload_time for cache validation check
    upload_time = ProjectMetadata(
        **project_mapping.Project.project_metadata
    ).get_upload_time()

    # `resource_id` not associated with `username`
    if not project_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )

    wb_analysis: dict
    ref_id_dict: dict[int, int]

    # Return from cache, if it exists and is valid
    if (
        cache
        and await cache.exists(f"wb:{resource_id}:analysis")
        and is_cache_valid(
            get_datetime(await cache.get(f"wb:{resource_id}:create_time")), upload_time
        )
    ):
        wb_analysis = await cache.get(f"wb:{resource_id}:analysis")
        wb_analysis = json.loads(wb_analysis)
        ref_id_dict = load_ref_ids(resource_id)

    # If not, process using Wildebeest
    else:
        try:
            wb_analysis, ref_id_dict = run_wildebeest_analysis(resource_id)

            if cache:
                async with cache.pipeline(transaction=True) as cache_pipeline:
                    await (
                        cache_pipeline.set(
                            f"wb:{resource_id}:analysis",
                            json.dumps(wb_analysis.analysis),
                        )
                        .set(
                            f"wb:{resource_id}:create_time",
                            datetime.now(timezone.utc).strftime(
                                DATETIME_TZ_FORMAT_STRING
                            ),
                        )
                        .execute()
                    )

            if not wb_analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Unable to find project contents.",
                )

            wb_analysis = wb_analysis.analysis

        except InputError as ine:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="There was an error while processing this request. Please try again.",
            )

    return templates.TemplateResponse(
        "wildebeest/analysis.fragment",
        {
            "request": request,
            "wb_analysis_data": wb_analysis,
            "ref_id_dict": ref_id_dict,
        },
    )
