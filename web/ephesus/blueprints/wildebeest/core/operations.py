"""
Operations run for the wildebeest blueprint
"""

# Core python imports
import json
import logging
from pathlib import Path
from datetime import datetime

# Third party
import flask
import wildebeest.wb_analysis as wb_ana

# This project
from web.ephesus.common.utils import (
    count_file_content_lines,
    is_file_modified,
)
from web.ephesus.model.common import (
    get_project_metadata,
    set_project_metadata,
)
from web.ephesus.extensions import cache


_LOGGER = logging.getLogger(__name__)


def get_wb_analysis(input_path, resource_id, vref_file_path=None):
    """Run Wildebeest analysis and return JSON results and optionally vref_dict"""
    _LOGGER.debug(f"Started running Wildebeest analysis on file: {input_path}")

    # Attempt to use a default vref_file if not provided
    if not vref_file_path:
        _LOGGER.debug(f"No vref_file provided. Attempting to use default...")
        # Load-in default vref_file
        # Taken from https://github.com/BibleNLP/ebible/blob/96e0c22a6ce6f3f50de60a6ac1ee30a057b9a5c0/metadata/vref.txt
        vref_file_path = Path(flask.current_app.config["GREEK_ROOM_DEFAULT_VREF_FILE"])

    # Correlate if number of lines in vref_file
    # and the input_path match, as a reasonable
    # assumption for a correct match.
    _LOGGER.debug(f"vref.txt line count = {count_file_content_lines(vref_file_path)}")
    _LOGGER.debug(
        f"{input_path.name} line count = {count_file_content_lines(input_path)}"
    )

    # There is a weird behavior where for some reason
    # python counts the parsed file as one line less.
    # wc -l seems to do the right thing. Assuming 1-off
    # is acceptable for now.
    if (
        count_file_content_lines(vref_file_path) - count_file_content_lines(input_path)
        > 1
    ):
        vref_dict = {}
        _LOGGER.info(
            f"Unable to use vref_file_path: {vref_file_path} due to total line count mismatch."
        )
    else:
        _LOGGER.debug(
            f"Successfully matched total line numbers with vref_file_path: {vref_file_path}"
        )

        vref_dict = wb_ana.load_ref_ids(vref_file_path)

    # Check if we can return from cache
    ## Get the project metadata
    project_metadata = get_project_metadata(resource_id)

    ## Get the last_modified_timestamp
    analysis_last_modified = project_metadata.setdefault("wildebeest", {}).setdefault(
        "AnalysisLastModified", datetime(2001, 1, 1).timestamp()
    )

    # See if we can use a cached response
    if cache.get(f"{input_path}") and not is_file_modified(
        input_path, analysis_last_modified
    ):
        wb_analysis = cache.get(f"{input_path}")
        _LOGGER.debug("Using cached Wildebeest output.")
    else:
        _LOGGER.debug("Running Wildebeest Analysis...")
        wb = wb_ana.process(in_file=f"{input_path}", ref_id_dict=vref_dict)
        _LOGGER.debug("Done.")
        wb_analysis = wb.analysis

        # set the cache and metadata
        cache.set(f"{input_path}", wb_analysis)

        project_metadata["wildebeest"][
            "AnalysisLastModified"
        ] = input_path.stat().st_mtime
        set_project_metadata(resource_id, project_metadata)

    _LOGGER.debug(f"Finished running Wildebeest analysis.")

    return wb_analysis, vref_dict
