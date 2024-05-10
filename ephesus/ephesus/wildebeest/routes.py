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
from fastapi.responses import (
    HTMLResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError

import redis.asyncio as redis

from ..config import get_ephesus_settings
from ..constants import (
    DATETIME_TZ_FORMAT_STRING,
    DATETIME_UTC_UI_FORMAT_STRING,
    WILDEBEEST_DOWNLOAD_FILENAME,
    ProjectMetadata,
)
from .core.wildebeest_util import (
    run_wildebeest_analysis,
    load_ref_ids,
    is_cache_valid,
    prettyprint_wildebeest_analysis,
)
from ..common.utils import (
    get_datetime,
    iter_file,
)
from ..dependencies import (
    get_db,
    get_cache,
    get_current_username,
)
from ..exceptions import InputError, OutputError
from ..database import crud
from ..database.schemas import ProjectAccessModel, WildebeestResultsModel

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
    cache: redis.client.Redis = Depends(get_cache),
) -> dict:
    """Get Wildebeest analysis results"""

    wb_results: WildebeestResultsModel = await process_wildebeest_analysis_request(
        resource_id, current_username, db, cache
    )

    return {
        "greek_room_metadata": {
            "project_name": wb_results["project_name"],
            "language_code": wb_results["lang_code"],
            "language_name": wb_results["lang_name"],
            "report_create_time": wb_results["report_create_time"].strftime(
                DATETIME_TZ_FORMAT_STRING
            ),
        },
        **wb_results["wb_analysis"],
    }


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

    wb_results: WildebeestResultsModel = await process_wildebeest_analysis_request(
        resource_id, current_username, db, cache
    )

    return templates.TemplateResponse(
        "wildebeest/analysis.fragment",
        {
            "request": request,
            "wb_analysis_data": wb_results["wb_analysis"],
            "ref_id_dict": wb_results["ref_id_dict"],
            "project_name": wb_results["project_name"],
            "lang_code": wb_results["lang_code"],
            "lang_name": wb_results["lang_name"],
            "report_create_time": wb_results["report_create_time"].strftime(
                DATETIME_UTC_UI_FORMAT_STRING
            ),
            "resource_id": resource_id,
        },
    )


@ui_router.get("/projects/{resource_id}/wildebeest/download")
def download_formatted_wildebeest_analysis(
    request: Request,
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Pretty print the wildebeest analysis results for direct download"""

    # Check if user has read access on project
    project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(
        db, resource_id, current_username
    )

    # `resource_id` not associated with `username`
    if not project_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )

    try:
        wb_prettyprint_filepath = prettyprint_wildebeest_analysis(resource_id)
        headers = {
            "Content-Disposition": f"attachment; filename={WILDEBEEST_DOWNLOAD_FILENAME.format(name=Path(wb_prettyprint_filepath).name)}"
        }

        # Write out Project metadata
        with open(wb_prettyprint_filepath, mode="a") as f:
            f.write(
                f"\nGREEK ROOM METADATA\n    Project Name: {project_mapping.Project.name}\n    Language Name: {'' if not project_mapping.Project.lang_name else project_mapping.Project.lang_name}\n    Language Code: {project_mapping.Project.lang_code}\n    Report Create Time: {datetime.now(timezone.utc).strftime(DATETIME_UTC_UI_FORMAT_STRING)}"
            )

        return StreamingResponse(
            iter_file(wb_prettyprint_filepath, mode="r", delete=True),
            media_type="text/plain; charset=UTF-8",
            headers=headers,
        )

    except OutputError as oute:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )


##########
# Common #
##########


async def process_wildebeest_analysis_request(
    resource_id: str,
    current_username: str,
    db: Session,
    cache: redis.client.Redis,
) -> WildebeestResultsModel:
    """
    Refactored common functionality for both
    Wildebeest Analysis UI and API endpoints
    """

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
    report_create_time: datetime = datetime.now(tz=timezone.utc)

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
        report_create_time = get_datetime(
            await cache.get(f"wb:{resource_id}:create_time")
        )
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

    return WildebeestResultsModel(
        wb_analysis=wb_analysis,
        ref_id_dict=ref_id_dict,
        report_create_time=report_create_time,
        project_name=project_mapping.Project.name,
        lang_code=project_mapping.Project.lang_code,
        lang_name=project_mapping.Project.lang_name,
    )
