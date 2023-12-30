"""
The utility module that contains logic to work with the Greek Room Wildebeest module
"""
import logging
import json
from pathlib import Path
from tempfile import TemporaryFile

from wildebeest import wb_analysis

from ...config import get_ephesus_settings
from ...exceptions import InputError
from ...constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()


def run_wildebeest_analysis(
    resource_id: str,
) -> (dict[str, any] | None, dict[int, str] | None):
    """
    Run the Wildebeest Analysis for the project `resource_id`.
    """
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

    try:
        ref_id_dict: dict[int, str] = wb_analysis.load_ref_ids(
            str(project_path / PROJECT_VREF_FILE_NAME)
        )
        return (
            wb_analysis.process(
                in_file=str(project_path / f"{resource_id}.txt"),
                ref_id_dict=ref_id_dict,
            ),
            ref_id_dict,
        )
    except Exception as exc:
        _LOGGER.exception(exc)
        raise InputError("Error while running Wildebeest analysis")
