import logging
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from ..config import get_ephesus_settings
from ..dependencies import (
    get_db,
)
from ..database.crud import (
    get_user_projects,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_setting = get_ephesus_settings()

# Configure templates
BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))

# Create UI router instance
ui_router = APIRouter()


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request, db: Session = Depends(get_db)):

    _LOGGER.debug(f"{ephesus_setting.ephesus_projects_dir}")

    get_user_projects(db, "my_username")

    # On first time login
    # create projects dirs
    # if not ephesus_setting.ephesus_projects_dir.exists():
    #     ephesus_setting.ephesus_projects_dir.mkdir(parents=True)

    return templates.TemplateResponse(
        "home/index.html",
        {"request": request},
    )
