"""
Utilities to in service of the spell checking interface
"""
import logging
from pathlib import Path

from ...config import (
    get_ephesus_settings,
    get_global_state,
)
# from ...exceptions import BoundsError
from ...constants import (
    LATEST_PROJECT_VERSION_NAME,
    PROJECT_CLEAN_DIR_NAME,
    PROJECT_VREF_FILE_NAME,
    BIBLENLP_RANGE_SYMBOL,
    GlobalStates,
    BibleReference,
)

# Get vendored deps
from ...vendor.spell_checker.bin import spell_check

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# My cheap cache
# TODO: Improve this by using redis.
# This would need for the spell_check
# model to be JSON serializable.
# Or better, the model is able to
# perform atomic updates without
# needing the whole class instance in-memory.
_spell_model_cache: dict[str, Any] = {}

def get_spell_checker_corpus(project_path: Path) -> dict[str, str]:
    """Utility to create a dict[ref] = verse from the project data"""
    try:
        with (project_path/PROJECT_VREF_FILE_NAME).open() as vref:
            for idx, line in enumerate(vref):
                line: str = line.strip()
                if not line:
                    continue

                books_chapters[book].add(chapter)

        return books_chapters

    except Exception as exc:
        _LOGGER.exception("Error while calculating scope of project. %s", exc)
        raise FormatError("Error while calculating scope of project.")



def get_spell_checker_model(data_filepath: Path, lang_code: str) -> spell_check.SpellCheckModel:
    """
    Initialize and get the Greek Room spell
    checker model for a given `resource_id`
    """

    # Initialize Greek Room spell checker model
    greek_room_spell_checker: spell_check.SpellCheckModel = spell_check.SpellCheckModel(project_mapping["Project"].lang_code)
    ephesus_settings.ephesus_projects_dir
                        / resource_id
                        / LATEST_PROJECT_VERSION_NAME
                        / PROJECT_CLEAN_DIR_NAME
                        / PROJECT_VREF_FILE_NAME

    books_chapters: dict[str, set(str)] = defaultdict(set)
    try:
        with vref_file.open() as vref:
            for idx, line in enumerate(vref):
                line: str = line.strip()
                if not line:
                    continue
                book: str = line.split()[0]
                chapter: str = line.split()[1].split(":")[0]
                books_chapters[book].add(chapter)

        return books_chapters

    greek_room_spell_checker.load_text_corpus(str(data_filepath), None)
    greek_room_spell_checker.test_spell_checker(ephesus_settings.ephesus_projects_dir
                                                / resource_id
                                                / LATEST_PROJECT_VERSION_NAME
                                                / PROJECT_CLEAN_DIR_NAME
                                                / f"{resource_id}.txt")
