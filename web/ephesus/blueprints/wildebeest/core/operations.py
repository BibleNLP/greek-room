"""
Operations run for the wildebeest blueprint
"""
# Core python imports
import json
import logging

# Third party
import wildebeest.wb_analysis as wb_ana

_LOGGER = logging.getLogger(__name__)


def get_wb_analysis(input_path):
    """Run Wildebeest analysis and return results in JSON"""
    _LOGGER.debug(f"Started running Wildebeest analysis on file: {input_path}")

    # TESTING
    with input_path.with_suffix(".json").open() as testing_file:
        return json.load(testing_file)

    # This returns a dict
    wb = wb_ana.process(in_file=f"{input_path}")

    _LOGGER.debug(f"Finished running Wildebeest analysis.")

    return wb.analysis
