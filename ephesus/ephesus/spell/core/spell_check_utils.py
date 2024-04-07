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

# from ...vendor.spell_checker.bin.spell_check import (
#     SpellCheckSuggestions,
#     SimpleWordEdge,
#     WordEdge,
# )

# Get app logger
_LOGGER = logging.getLogger(__name__)

# Get app settings
ephesus_settings = get_ephesus_settings()

# My cheap cache:
# dict[(current_username, resource_id)] = spell_check.SpellCheckModel
# TODO: Improve this by using redis.
# This would need for the spell_check
# model to be JSON serializable.
# Or better, the model is able to
# perform atomic updates without
# needing the whole class instance in-memory.
_spell_check_model_cache: dict[(str, str), Any] = {}

def get_spell_checker_data(project_path: Path, resource_id: str, lang_code: str) -> (dict[str, str], dict[(str, str), int]):
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


def get_spell_check_model(current_username: str, resource_id: str, lang_code: str) -> spell_check.SpellCheckModel:
    """
    Initialize and get the Greek Room spell
    checker model for a given `resource_id`
    """
    # Attempt to obtain model from cache
    if (current_username, resource_id) in _spell_check_model_cache:
        _LOGGER.debug("Cache hit for spell_check_model")
        return _spell_check_model_cache[(current_username, resource_id)]

    project_path: Path = ephesus_settings.ephesus_projects_dir / resource_id / LATEST_PROJECT_VERSION_NAME / PROJECT_CLEAN_DIR_NAME

    # Initialize Greek Room spell checker model
    greek_room_spell_checker: spell_check.SpellCheckModel = spell_check.SpellCheckModel(lang_code)

    # Load data in model
    greek_room_spell_checker.load_text_corpus(text_filename=str(project_path/f"{resource_id}.txt"),
                                              snt_id_data=str(project_path/PROJECT_VREF_FILE_NAME))

    # greek_room_spell_checker.corpus, greek_room_spell_checker.word_count = get_spell_checker_data(project_path, resource_id, lang_code)

    # Set cache
    _spell_check_model_cache[(current_username, resource_id)] = greek_room_spell_checker

    return greek_room_spell_checker


def get_verse_suggestions(verse: str, suggestions: spell_check.SpellCheckSuggestions):
    """
    Incorporate the checking suggestions to the full
    verse text for easier manipulation in the UI.
    """
    # Crazy logic to find the tuple of indices
    # that are *not* covered by `suggestsions`
    edges_set: set = set()
    super_set: set = set(list(range(len(verse)+1)))

    for word_edge in suggestions.d.keys():
        # Populate edges_set
        for simple_word_edge in word_edge.edges:
            edges_set.update(list(range(simple_word_edge.start, simple_word_edge.end)))

        # Also, use this loop for
        # marshalling the suggestions for UI
        suggestions.d[word_edge] = [{"word": alt.txt, "count": alt.count, "cost": alt.cost} for alt in suggestions.d[word_edge].alt_spellings]


    leftovers = sorted(super_set-edges_set)
    leftover_edges = []
    i = 0
    while i<len(leftovers)-1:
        leftover_edge = [leftovers[i]]
        y=i
        while y<len(leftovers)-1:
            if leftovers[y+1] == leftovers[y] + 1:
                i += 1
                y += 1
                continue
            else:
                break

        leftover_edge.append(leftovers[i]+1)
        leftover_edges.append(leftover_edge)
        i += 1

    # Stitch-in the leftover indices with no real suggestions
    for leftover_edge in leftover_edges:
        suggestions.d[spell_check.WordEdge([spell_check.SimpleWordEdge('', leftover_edge[0], leftover_edge[1])])] = None

    suggestions.d = dict(sorted(suggestions.d.items(), key=lambda x: x[0].edges[0].start))

    return suggestions
