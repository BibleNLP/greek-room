import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import get_ephesus_settings

ephesus_setting = get_ephesus_settings()

BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
ui_router = APIRouter()

# Get app logger
_LOGGER = logging.getLogger(__name__)


@ui_router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):

    _LOGGER.debug(f"{ephesus_setting.ephesus_projects_dir}")

    return templates.TemplateResponse(
        "home/index.html",
        {"request": request},
    )
