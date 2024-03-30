"""
Utilities to in service of the spell checking interface
"""
# debug
import sys

import logging
from typing import Any
from pathlib import Path
from collections import defaultdict

from ...config import (
    get_ephesus_settings,
    get_global_state,
)
from ...exceptions import FormatError
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

def get_spell_checker_data(project_path: Path, resource_id: str, lang_code: str) -> dict[str, str]:
    """Utility to create a dict[ref] = verse from the project data. Also, return dict[(lcode, word)] = word_frequency"""
    try:
        corpus: dict[str, str] = {}
        word_count: dict[(str, str), int] = defaultdict(int)
        with (project_path/PROJECT_VREF_FILE_NAME).open() as vref_file, (project_path/f"{resource_id}.txt").open() as bible_file:
            for idx, (vref, verse) in enumerate(zip(vref_file, bible_file)):
                vref = vref.strip()
                if not vref:
                    continue

                corpus[vref] = verse.strip()
                for word in spell_check.words_in_snt(verse.strip()):
                    word_count[(lang_code, word)] += 1

        return corpus, word_count

    except Exception as exc:
        _LOGGER.exception("Error while creating corpus object. %s", exc)
        raise FormatError("Error while creating corpus object.")


def get_spell_checker_model(resource_id: str, lang_code: str) -> spell_check.SpellCheckModel:
    """
    Initialize and get the Greek Room spell
    checker model for a given `resource_id`
    """
    project_path: Path = ephesus_settings.ephesus_projects_dir    / resource_id    / LATEST_PROJECT_VERSION_NAME    / PROJECT_CLEAN_DIR_NAME

    # Initialize Greek Room spell checker model
    greek_room_spell_checker: spell_check.SpellCheckModel = spell_check.SpellCheckModel(lang_code)

    greek_room_spell_checker.corpus, greek_room_spell_checker.word_count = get_spell_checker_data(project_path, resource_id, lang_code)

    test_snt1 = 'advisors heven blesing son Beersheba'
    test_snt2 = 'advisers heaven blessing son California'
    print(test_snt1)
    sc_suggestions = greek_room_spell_checker.spell_check_snt(test_snt1, 'test')
    print(sc_suggestions)
    wc_words = ['the', 'heven', 'advisers', 'advisors', 'California']
    print(greek_room_spell_checker.show_selected_word_counts(wc_words))
    greek_room_spell_checker.update_snt(test_snt1, 'test', log=sys.stdout)
    print(greek_room_spell_checker.show_selected_word_counts(wc_words))
    greek_room_spell_checker.update_snt(test_snt2, 'test', old_snt=test_snt1, log=sys.stdout)
    print(greek_room_spell_checker.show_selected_word_counts(wc_words))
    print(greek_room_spell_checker.spell_check_snt('Californie', 'test'))
