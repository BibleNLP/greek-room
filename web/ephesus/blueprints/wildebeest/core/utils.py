"""
Utilities in service of the wildebeest blueprint
"""

# Core python imports
import json
import logging
import zipfile

# Third party
from machine.corpora import (
    extract_scripture_corpus,
    ParatextTextCorpus,
)

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
    # already in the BibleNLP verse-wise lined format
    if filepath.suffix.lower() in [".txt"]:
        filepath.replace(f"{filepath.parent / resource_id}.txt")

    # Handle Zipped Paratext project uploads
    elif filepath.suffix.lower() in [".zip"]:
        extract_path = filepath.parent / "extract"
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        # Read in Paratext project
        paratext_corpus = ParatextTextCorpus(f"{extract_path}")

        # Extract into BibleNLP format
        # This returns verse_text, org_versification, corpus_versification. We don't want to map to org for this use-case.
        verses = []
        vrefs = []
        for verse, _, vref in extract_scripture_corpus(paratext_corpus):
            verses.append(verse)
            vrefs.append(str(vref))

        # Write full output to a single file
        with (filepath.parent / f"{resource_id}.txt").open("w") as parsed_file:
            parsed_file.write("\n".join(verses))

        # Write corresponding vref.txt file
        with (filepath.parent / "vref.txt").open("w") as vref_file:
            vref_file.write("\n".join(vrefs))
