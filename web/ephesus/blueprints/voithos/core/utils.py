"""
Utilities in service of the word checker prototype
"""
# Core python imports
import json
import logging

# This project
from web.ephesus.constants import BookCodes
from web.ephesus.exceptions import InternalError

from web.ephesus.common.ingester import (
    TSVDataExtractor,
    USFMDataExtractor,
)

_LOGGER = logging.getLogger(__name__)


def parse_upload_file(filepath, resource_id):
    """Parse and store the uploaded input file as JSON"""
    if filepath.suffix.lower() in [".sfm", ".usfm"]:
        parser = USFMDataExtractor(str(filepath))
    elif filepath.suffix.lower() in [".tsv"]:
        parser = TSVDataExtractor(str(filepath.parent))

    with open(f"{filepath.parent / resource_id}.json", "w") as json_file:
        json.dump(parser.data, json_file)


def update_file_content(filepath, json_content):
    """Write updated JSON content back to file"""
    if not json_content or len(json_content) == 0:
        raise InternalError()

    with open(filepath, "w") as json_file:
        json.dump(json_content, json_file)
