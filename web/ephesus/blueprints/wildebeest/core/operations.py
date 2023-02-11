"""
Operations run for the wildebeest blueprint
"""
# Core python imports
import json
import logging
from pathlib import Path

# Third party
import flask
import wildebeest.wb_analysis as wb_ana

# This project
from web.ephesus.common.utils import (
    count_file_lines,
)


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
        _LOGGER.info(count_file_lines(input_path))
        _LOGGER.info(len(ref_id_dict))
        if len(ref_id_dict) != count_file_lines(input_path):
            ref_id_dict = None

    # TESTING
    with input_path.with_suffix(".json").open() as testing_file:
        return json.load(testing_file), ref_id_dict

    _LOGGER.info(ref_id_dict)
    wb = wb_ana.process(in_file=f"{input_path}", ref_id_dict=ref_id_dict)

    _LOGGER.debug(f"Finished running Wildebeest analysis.")

    return wb.analysis, ref_id_dict
