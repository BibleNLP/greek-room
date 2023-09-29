"""
Common utitities shared across blueprints
"""

# Core python imports
import json
import string
import logging
import zipfile
from pathlib import Path
from datetime import datetime
from collections import namedtuple

# This project
from web.ephesus.constants import (
    ProjectTypes,
)
from web.ephesus.exceptions import (
    ProjectError,
    InputError,
)

# Third party
from machine.corpora import (
    UsfmFileTextCorpus,
    extract_scripture_corpus,
    ParatextTextCorpus,
)

_LOGGER = logging.getLogger(__name__)


def sanitize_string(user_input):
    """Simple sanitizer for form user input"""
    whitelist = string.ascii_letters + string.digits + " _.,:-()&"
    return "".join([letter for letter in user_input][:15])


def parse_uploaded_files(filepath, resource_id):
    """Parse and store the uploaded input files"""

    try:
        # If the input is .txt, assume it is
        # already in the BibleNLP verse-wise lined format
        if filepath.suffix.lower() in [".txt"]:
            filepath.replace(f"{filepath.parent / resource_id}.txt")

        # Handle Zipped project uploads
        # These can either by Paratext Projects or
        # a simple collection of USFM files
        # (with .sfm or .usfm extensions).
        elif filepath.suffix.lower() in [".zip"]:
            extract_dir = filepath.parent / "extract"
            with zipfile.ZipFile(filepath, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Check if this is a Paratext Project
            # See https://github.com/sillsdev/machine.py/blob/19188e173ffdd3c22f2c4eaa68c581d72f2c86c5/machine/corpora/paratext_text_corpus.py#L55C12-L55C12
            if (
                is_generator_valid(extract_dir.glob("*.SFM"))
                and (extract_dir / "Settings.xml").exists()
            ):
                extracted_corpus = ParatextTextCorpus(str(extract_dir))

            # Otherwise check if it uses any of the
            # other reasonable USFM file extensions
            elif is_generator_valid(extract_dir.glob("*.SFM")):
                extracted_corpus = UsfmFileTextCorpus(str(extract_dir))
            elif is_generator_valid(extract_dir.glob("*.sfm")):
                extracted_corpus = UsfmFileTextCorpus(
                    str(extract_dir), file_pattern="*.sfm"
                )
            elif is_generator_valid(extract_dir.glob("*.usfm")):
                extracted_corpus = UsfmFileTextCorpus(
                    str(extract_dir), file_pattern="*.usfm"
                )
            elif is_generator_valid(extract_dir.glob("*.USFM")):
                extracted_corpus = UsfmFileTextCorpus(
                    str(extract_dir), file_pattern="*.USFM"
                )

            # Extract into BibleNLP format
            # This returns verse_text, org_versification, corpus_versification. We don't want to map to org for this use-case.
            verses = []
            vrefs = []
            for verse, _, vref in extract_scripture_corpus(extracted_corpus):
                verses.append(verse)
                vrefs.append(str(vref))

            # Write full output to a single file
            with (filepath.parent / f"{resource_id}.txt").open("w") as parsed_file:
                parsed_file.write("\n".join(verses))

            # Write corresponding vref.txt file
            with (filepath.parent / "vref.txt").open("w") as vref_file:
                vref_file.write("\n".join(vrefs))
    except Exception as e:
        _LOGGER.error("Error while parsing and saving the data", e)
        raise InputError("Error while processsing the data.")


def is_generator_valid(gen):
    """Utility to check if a generator has any valid value in at-all or not.
    This is a subsitute for `len` checks for generators"""
    if not gen:
        return False

    try:
        next(gen)
    except StopIteration as s:
        return False

    # Seems there is at-least one value
    return True


def get_projects_listing(username, base_path, roles=[]):
    """
    Get the listing of the projects for use in the UI.
    This is derived from reading the metadata.json file
    assumed to be in sub-directories within the `base_path`.
    """
    ProjectDetails = namedtuple(
        "ProjectDetails", ["resource_id", "project_name", "lang_code", "birth_time"]
    )
    project_listing = []
    # Set ops are more elegant than array ops
    roles = set(roles)
    for resource in base_path.iterdir():
        if resource.name.startswith("."):
            continue

        try:
            # Read metadata.json
            with (resource / "metadata.json").open() as metadata_file:
                metadata = json.load(metadata_file)

            if (
                username == metadata.get("owner", None)
                or len(roles.intersection(metadata.get("tags", []))) > 0
            ):
                project_listing.append(
                    ProjectDetails(
                        resource.name,
                        metadata["projectName"],
                        metadata["langCode"],
                        resource.stat().st_ctime,
                    )
                )
        except FileNotFoundError as e:
            _LOGGER.error(
                f"Unable to find metadata.json but ignoring this for now.",
                exc_info=True,
            )
            pass

    return sorted(project_listing, reverse=True, key=lambda x: x.birth_time)


def count_file_content_lines(file_path):
    """Return the number of lines in `file_path`"""
    with file_path.open() as f:
        for count, line in enumerate(f):
            pass

        return count + 1


def is_file_modified(file_path, last_modified):
    """Checks if `file_path` has a newer modified date than `last_modified`"""
    if not file_path or not last_modified:
        return False

    return datetime.fromtimestamp(file_path.stat().st_mtime) > datetime.fromtimestamp(
        last_modified
    )
