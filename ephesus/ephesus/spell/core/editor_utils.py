"""
Module with logic to work with the Greek Room Spell Checker Editor
"""
import logging
import fileinput
from pathlib import Path
from itertools import islice

from ...config import (
    get_ephesus_settings,
    get_global_state,
)
from ...exceptions import (
    BoundsError,
    InputError
)
from ...constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
    BIBLENLP_RANGE_SYMBOL,
    GlobalStates,
    BibleReference,
)

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()


def get_chapter_content(resource_id: str, ref: BibleReference) -> list[str]:
    """Get the `ref` (chapter) content to show in editor"""
    if not ref.chapter:
        raise BoundsError("Unable to find the chapter reference")

    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
        / PROJECT_CLEAN_DIR_NAME
    )

    if not all(
        [
            project_path.exists(),
            (project_path / f"{resource_id}.txt").exists(),
            (project_path / PROJECT_VREF_FILE_NAME).exists(),
        ]
    ):
        _LOGGER.error("Unable to find content files for project %s", resource_id)
        raise InputError("Unable to find content files for project %s", resource_id)

    vref_bounds: list[int] = get_global_state(GlobalStates.VREF_INDEX)[ref.book][ref.chapter]
    verses: list[list[str]] = []
    with(project_path / f"{resource_id}.txt").open() as bible_file:
        for idx, line in enumerate(islice(bible_file,
                                          vref_bounds[0],
                                          vref_bounds[1]+1), 1):

            # Handle verse ranges
            if line.strip() == BIBLENLP_RANGE_SYMBOL:
                verses[-1][0] = f"{verses[-1][0].split('-')[0]}-{idx}"
                continue

            verses.append([str(idx), line.strip()])

    return verses

def set_verse_content(resource_id: str, ref: BibleReference, verse: str) -> None:
    """Write verse text to file. Used for updating text."""
    if not ref.chapter or not ref.verse:
        raise BoundsError("Unable to find the chapter or verse from reference")

    project_path: Path = (
        ephesus_settings.ephesus_projects_dir
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
        / PROJECT_CLEAN_DIR_NAME
    )

    if not all(
        [
            project_path.exists(),
            (project_path / f"{resource_id}.txt").exists(),
            (project_path / PROJECT_VREF_FILE_NAME).exists(),
        ]
    ):
        _LOGGER.error("Unable to find content files for project %s", resource_id)
        raise InputError("Unable to find content files for project %s", resource_id)

    vref_bounds: list[int] = get_global_state(GlobalStates.VREF_INDEX)[ref.book][ref.chapter]

    # Handle verse ranges
    if "-" in ref.verse:
        ref.verse = ref.verse.split("-")[0]

    bible_line_no: int = vref_bounds[0] + int(ref.verse)

    with fileinput.input(files=(str(project_path / f"{resource_id}.txt")), inplace=True) as bible_file:
        for line in bible_file:
            if fileinput.filelineno() == bible_line_no:
                # TODO: Test more to see if this has issues
                print(verse)
            else:
                print(line, end="")
