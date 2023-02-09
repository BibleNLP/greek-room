"""
Common utitities shared across blueprints
"""

# Core python imports
import json
import string
import logging
from collections import namedtuple

_LOGGER = logging.getLogger(__name__)


def sanitize_string(user_input):
    """Simple sanitizer for form user input"""
    whitelist = string.ascii_letters + string.digits + " _.,:-()&"
    return "".join([letter for letter in user_input][:15])


def get_projects_listing(base_path):
    """Get the listing of the projects for use on the UI"""
    ProjectDetails = namedtuple(
        "ProjectDetails", ["resource_id", "project_name", "lang_code", "birth_time"]
    )
    project_listing = []
    for resource in base_path.iterdir():
        if resource.name.startswith("."):
            continue

        # Read metadata.json
        with (resource / "metadata.json").open() as metadata_file:
            metadata = json.load(metadata_file)

        project_listing.append(
            ProjectDetails(
                resource.name,
                metadata["projectName"],
                metadata["langCode"],
                resource.stat().st_birthtime,
            )
        )

    return sorted(project_listing, reverse=True, key=lambda x: x.birth_time)