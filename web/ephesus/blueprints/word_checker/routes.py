"""
Parent module for the "spell checker" Flask blueprint

This blueprint is a prototype of the backend for the word-level checks.
e.g. spellings and word suggestions.
"""
#
# Imports
#

# Core python imports
import logging

# 3rd party imports
import flask

# This project
from .core.utils import TSVDataExtractor
from .core.spell_checker import SpellChecker

#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "word_checker",
    __name__,
    url_prefix="/word_checker",
    template_folder="templates",
    static_folder="static",
)

#
# Routes
#


@BP.route("/")
@BP.route("/index.html")
def get_index():
    """Get the root index for the blueprint"""
    tsv_extractor = TSVDataExtractor(f'{flask.current_app.config["DATA_PATH"]}/en_ult')
    return flask.render_template(
        "word_checker/index.html", scripture_data=tsv_extractor.data
    )


@BP.route("/home")
def get_home():
    """Get the home page for the blueprint"""
    return flask.render_template("word_checker/home.html")


@BP.route("/api/v1/spell-checker")
def get_spell_suggestions():
    spell_checker = SpellChecker(data="")
    _LOGGER.debug(spell_checker.get_spell_suggestions())
    return {"spellSuggestions": spell_checker.get_spell_suggestions()}
