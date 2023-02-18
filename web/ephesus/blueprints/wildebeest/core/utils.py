"""
Utilities in service of the wildebeest blueprint
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


def parse_uploaded_files(filepath, resource_id):
    """Parse and store the uploaded input files"""

    # If the input is .txt, assume it is
    # already in the NLP verse-wise lined format
    if filepath.suffix.lower() in [".txt"]:
        filepath.replace(f"{filepath.parent / resource_id}.txt")
