"""
API and UI routes for spell check
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
    status,
    HTTPException,
)
from fastapi.responses import (
    HTMLResponse,
)
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError

from ..config import get_ephesus_settings
from ..constants import (
    BibleReference,
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
)
from ..common.utils import (
    get_scope_from_vref,
    get_scope_from_vref,
)
from ..dependencies import (
    get_db,
    get_current_username,
)
from ..exceptions import InputError, OutputError
from .core.editor_utils import (
    get_chapter_content,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# Configure templates
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))


#############
# UI Routes #
#############

# Create UI router instance
ui_router = APIRouter(
    tags=["ui"],
)


@ui_router.get("/projects/{resource_id}/spell", response_class=HTMLResponse)
async def get_editor(
    request: Request,
    resource_id: str,
    current_username: str = Depends(get_current_username),
):
    """Get the spell checking UI"""
    # Get nav bar data
    project_scope: dict[str, set] = get_scope_from_vref(ephesus_settings.ephesus_projects_dir
                        / resource_id
                        / LATEST_PROJECT_VERSION_NAME
                        / PROJECT_CLEAN_DIR_NAME
                        / PROJECT_VREF_FILE_NAME)

    return templates.TemplateResponse(
        "spell/editor-pane.html",
        {
            "request": request,
            "resource_id": resource_id,
            "project_scope": project_scope
        },
    )


@ui_router.get("/projects/{resource_id}/verses", response_class=HTMLResponse)
async def get_verses(
        request: Request,
        resource_id: str,
        ref: str,
):
    """Get the verses content"""
    bible_ref: BibleReference = BibleReference.from_string(ref)
    verses: list[list[str]] = get_chapter_content(resource_id, bible_ref)

    return templates.TemplateResponse(
        "spell/editor.fragment",
        {
            "request": request,
            "ref": f"{bible_ref.book} {bible_ref.chapter}",
            "verses": verses
        },
    )
