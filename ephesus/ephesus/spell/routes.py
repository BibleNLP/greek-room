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
from ..constants import BibleReference
from ..common.utils import (
    get_datetime,
    iter_file,
    get_scope_from_vref,
)
from ..dependencies import (
    get_db,
    get_current_username,
)
from ..exceptions import InputError, OutputError
from ..database import crud
from ..database.schemas import ProjectAccessModel

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
    ref: str,
    resource_id: str,
    current_username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Get the spell checking UI"""
    bible_ref: BibleReference = BibleReference.from_string(ref)
    return templates.TemplateResponse(
        "spell/editor.fragment",
        {
            "request": request,
            "ref_id_dict": wb_results["ref_id_dict"],
        },
    )
