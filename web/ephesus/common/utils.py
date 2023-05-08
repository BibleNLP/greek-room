"""
Common utitities shared across blueprints
"""

# Core python imports
import json
import string
import logging
from datetime import datetime
from collections import namedtuple

# This project
from web.ephesus.constants import (
    ProjectTypes,
)
from web.ephesus.exceptions import (
    ProjectError,
)

_LOGGER = logging.getLogger(__name__)


def sanitize_string(user_input):
    """Simple sanitizer for form user input"""
    whitelist = string.ascii_letters + string.digits + " _.,:-()&"
    return "".join([letter for letter in user_input][:15])


def get_projects_listing(
    username, base_path, roles=[], project_type=ProjectTypes.PROJ_WILDEBEEST
):
    """
    Get the listing of the projects for use in the UI.
    This is derived from reading the metadata.json file
    assumed to be in sub-directories within the `base_path`.
    """
    ProjectDetails = namedtuple(
        "ProjectDetails", ["resource_id", "project_name", "lang_code", "birth_time"]
    )
    project_listing = []
    # Set ops are more elegant than array ops
    roles = set(roles)
    for resource in base_path.iterdir():
        if resource.name.startswith("."):
            continue

        try:
            # Read metadata.json
            with (resource / "metadata.json").open() as metadata_file:
                metadata = json.load(metadata_file)

            if (
                username == metadata.get("owner", None)
                or len(roles.intersection(metadata.get("tags", []))) > 0
            ):
                project_listing.append(
                    ProjectDetails(
                        resource.name,
                        metadata["projectName"],
                        metadata["langCode"],
                        resource.stat().st_ctime,
                    )
                )
        except FileNotFoundError as e:
            _LOGGER.error(
                f"Unable to find metadata.json but ignoring this for now.",
                exc_info=True,
            )
            pass

    return sorted(project_listing, reverse=True, key=lambda x: x.birth_time)


def count_file_content_lines(file_path):
    """Return the number of lines in `file_path`"""
    with file_path.open() as f:
        for count, line in enumerate(f):
            pass

        return count + 1


def is_file_modified(file_path, last_modified):
    """Checks if `file_path` has a newer modified date than `last_modified`"""
    if not file_path or last_modified:
        return False

    return datetime.fromtimestamp(file_path.stat().st_mtime) > datetime.fromtimestamp(
        last_modified
    )
