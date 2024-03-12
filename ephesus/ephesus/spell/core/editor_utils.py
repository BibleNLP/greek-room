"""
Module with logic to work with the Greek Room Spell Checker
"""
import logging
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import (
    datetime,
)

from ...config import (
    get_ephesus_settings,
    get_global_state,
)
from ...exceptions import BoundsError
from ...constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
    GlobalStates,
    BibleReference,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()


def get_chapter_content(resource_id: str, ref: BibleReference) -> list[str] | None:
    """Get the `ref` (chapter) content to show in editor"""
    if not ref.chapter:
        raise BoundsError("Unable to find the chapter reference")
    _LOGGER.debug(get_global_state(GlobalStates.VREF_INDEX))
    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
        / PROJECT_CLEAN_DIR_NAME
    )

    if not all(
        [
            project_path.exists(),
            (project_path / f"{resource_id}.txt").exists(),
            (project_path / PROJECT_VREF_FILE_NAME).exists(),
        ]
    ):
        _LOGGER.error("Unable to find content files for project %s", resource_id)
        return None

    verses: list[str] = []
    with(project_path / f"{resource_id}.txt").open() as bible_file:
        is_chapter: bool = False
        for idx, line in enumerate(bible_file):

            if is_chapter and :
                verses.append(line.strip())

            # Get the chapter start line no.
            if idx == get_global_state(GlobalStates.VREF_INDEX)[ref.book][ref.chapter]:
                is_chapter = True
