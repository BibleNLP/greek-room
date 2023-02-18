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
from web.ephesus.extensions import cache


_LOGGER = logging.getLogger(__name__)


def get_wb_analysis(input_path, ref_id_file_path=None):
    """Run Wildebeest analysis and return JSON results and optionally ref_id_dict"""
    _LOGGER.debug(f"Started running Wildebeest analysis on file: {input_path}")

    # Attempt to use a default ref_id_file if not provided
    if not ref_id_file_path:
        _LOGGER.debug(f"No ref_id_file provided. Attempting to use default...")
        # Load-in default ref_id_file
        # Taken from https://github.com/BibleNLP/ebible/blob/96e0c22a6ce6f3f50de60a6ac1ee30a057b9a5c0/metadata/vref.txt
        ref_id_file_path = Path(
            flask.current_app.config["WILDEBEEST_DEFAULT_REF_ID_FILE"]
        )
        ref_id_dict = wb_ana.load_ref_ids(ref_id_file_path)

        # Correlate if number of lines in ref_id_file
        # and the input_path match, as a reasonable
        # assumption for a correct match.
        if len(ref_id_dict) != count_file_content_lines(input_path):
            ref_id_dict = {}
            _LOGGER.debug(
                "Unable to use the default ref_id_file due to total line count mismatch."
            )
        else:
            _LOGGER.debug(
                "Successfully matched total line numbers; using default ref_id_file."
            )

    # Check if we can return from cache
    ## Get the metadata.json
    with (input_path.parent / "metadata.json").open() as metadata_file:
        metadata = json.load(metadata_file)

    ## Get the last_modified_timestamp
    last_modified = metadata.get(
        "wbAnalysisLastModified", datetime(2001, 1, 1).timestamp()
    )

    if cache.get(f"{input_path}") and not is_file_modified(input_path, last_modified):
        wb_analysis = cache.get(f"{input_path}")
        _LOGGER.debug("Using cached Wildebeest output.")
    else:
        _LOGGER.debug("Running Wildebeest Analysis...")
        wb = wb_ana.process(in_file=f"{input_path}", ref_id_dict=ref_id_dict)
        _LOGGER.debug("Done.")
        wb_analysis = wb.analysis

        # set the cache and metadata
        cache.set(f"{input_path}", wb_analysis)
        metadata["wbAnalysisLastModified"] = input_path.stat().st_mtime
        with (input_path.parent / "metadata.json").open("w") as metadata_file:
            json.dump(metadata, metadata_file)

    _LOGGER.debug(f"Finished running Wildebeest analysis.")

    return wb_analysis, ref_id_dict
