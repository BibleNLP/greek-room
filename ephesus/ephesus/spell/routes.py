"""
API and UI routes for spell check
"""

import json
import logging
from pathlib import Path
import random
import secrets
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
)
from .core.spell_check_utils import (
    get_spell_check_model,
)
from ..dependencies import (
    get_db,
    get_current_username,
)
from ..database import crud, schemas
from ..exceptions import InputError, OutputError
from .core.editor_utils import (
    get_chapter_content,
)

from ..vendor.spell_checker.bin.spell_check import (
    SpellCheckModel,
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
    db: Session = Depends(get_db),
    current_username: str = Depends(get_current_username),
):
    """Get the spell checking UI"""

    # Get project language code
    project_mapping: schemas.ProjectWithAccessModel | None = crud.get_user_project(db, resource_id, current_username)

    # Project not found.
    # Not returning a 404 for security sake.
    if not project_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There was an error while processing this request. Please try again.",
        )

    # Get nav bar data
    project_scope: dict[str, set] = get_scope_from_vref(ephesus_settings.ephesus_projects_dir
                        / resource_id
                        / LATEST_PROJECT_VERSION_NAME
                        / PROJECT_CLEAN_DIR_NAME
                        / PROJECT_VREF_FILE_NAME)

    spell_check_model: SpellCheckModel = get_spell_check_model(current_username, resource_id, project_mapping["Project"].lang_code)

    return templates.TemplateResponse(
        "spell/editor-pane.html",
        {
            "request": request,
            "resource_id": resource_id,
            "project_scope": project_scope
        },
    )


@ui_router.get("/projects/{resource_id}/chapter", response_class=HTMLResponse)
async def get_chapter(
        request: Request,
        resource_id: str,
        ref: str,
):
    """Get the verses content"""
    bible_ref: BibleReference = BibleReference.from_string(ref)
    verses: list[list[str]] = get_chapter_content(resource_id, bible_ref)

    # Create dummy data
    dummy_data: list[list] = []
    for verse in verses:
        verse_dummy_data = []
        for word in verse[1].split():
            if random.randint(0, 10) < 5:
                verse_dummy_data.append({"count": random.randint(0, 10), "spellSuggestions": [{"alternativeSpelling": secrets.token_urlsafe(5), "count": random.randint(0, 100), "smartEditDistance": round(random.uniform(0, 3), 2)}, {"alternativeSpelling": secrets.token_urlsafe(5), "count": random.randint(0, 100), "smartEditDistance": round(random.uniform(0, 3), 2)}, {"alternativeSpelling": secrets.token_urlsafe(5), "count": random.randint(0, 100), "smartEditDistance": round(random.uniform(0, 3), 2)}]})
            else:
                verse_dummy_data.append({"count": random.randint(0, 10)})
        dummy_data.append(verse_dummy_data)


    return templates.TemplateResponse(
        "spell/chapter.fragment",
        {
            "request": request,
            "ref": f"{bible_ref.book} {bible_ref.chapter}",
            "verses": verses,
            "dummy_data": dummy_data,
        },
    )
