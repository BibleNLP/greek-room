"""
Parent module for the "example" Flask blueprint

Intended to provide a working example of a non-root Flask blueprint in this app.
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
    "example",
    __name__,
    url_prefix="/example",
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
    return flask.render_template("example/index.html")
