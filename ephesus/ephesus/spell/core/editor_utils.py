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
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()


def get_chapter_content(resource_id: str, ref: BibleReference):
    """Get the `ref` (chapter) content to show in editor"""
    if not ref.chapter:
        raise BoundsError("Unable to find the chapter reference")
    # get_global_state
