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
    _LOGGER.info(f'Config Settings {flask.current_app.config["DATA_PATH"]}')
    return flask.render_template("word_checker/index.html")
