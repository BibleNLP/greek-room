"""
The utility module that contains logic to work with the Greek Room Wildebeest module
"""
import logging
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import (
    datetime,
)


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
        return None, None

    try:
        ref_id_dict: dict[int, str] = load_ref_ids(resource_id)
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


def prettyprint_wildebeest_analysis(
    resource_id: str,
) -> str | None:
    """
    Run the Wildebeest Analysis for the project `resource_id`
    and write results in a text file and return the filename.
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
        ref_id_dict: dict[int, str] = load_ref_ids(resource_id)

        with NamedTemporaryFile(mode="w", delete=False) as fp:
            wb_analysis.process(
                in_file=str(project_path / f"{resource_id}.txt"),
                ref_id_dict=ref_id_dict,
                pp_output=fp,
            )
            return fp.name

    except Exception as exc:
        _LOGGER.exception(exc)
        raise InputError("Error while running Wildebeest analysis")


def load_ref_ids(resource_id: str) -> dict[int, int]:
    """Load reference IDs from a path; uses Wildebeest"""
    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
        / PROJECT_CLEAN_DIR_NAME
    )
    return wb_analysis.load_ref_ids(str(project_path / PROJECT_VREF_FILE_NAME))


def is_cache_valid(cached_time: datetime, upload_time: datetime) -> bool:
    """
    If the cached_time is prior to upload_time,
    the cache is invalid and should be refreshed
    """
    if not cached_time or not upload_time:
        return False

    if upload_time > cached_time:
        return False

    return True
