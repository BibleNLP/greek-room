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

        file_content = open(filepath, encoding="utf-8", errors="surrogateescape").read()
        usfm_parser = USFMParser(file_content)

        # Get verses list from USFM
        verses = usfm_parser.to_list([Filter.SCRIPTURE_TEXT])

        # Create references dict
        ref_id_dict = {
            idx: f"{row[0]} {row[1]}:{row[2]}" for idx, row in enumerate(verses[1:])
        }

        # Clean out references
        verses = [v[3].strip('"').strip() for v in verses[1:]]

        _LOGGER.debug("Finished work to parse file")

        return verses, ref_id_dict
    except Exception as e:
        _LOGGER.error("Error while parsing file", e)
