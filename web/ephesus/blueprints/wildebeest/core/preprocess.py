"""
Script to preprocess the input USFM files
to convert them into a format that can be
run with Wildebeest.
"""

import logging

from usfm_grammar import USFMParser, Filter

_LOGGER = logging.getLogger(__name__)


def parse_usfm(filepath):
    """Get verse content from USFM"""
    try:
        _LOGGER.debug("Starting work to parse file")

        file_content = open(filepath).read()
        usfm_parser = USFMParser(file_content)
        return usfm_parser.to_list([Filter.SCRIPTURE_TEXT])

        _LOGGER.debug("Finished work to parse file")
    except Exception as e:
        _LOGGER.error("Error while parsing file", e)
