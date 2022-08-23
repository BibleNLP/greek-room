"""
Parent module for the "Alignment Developer Visualization (align_dev_viz)" Flask blueprint

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
    "align_dev_viz",
    __name__,
    url_prefix="/align_dev_viz",
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
    return flask.render_template("align_dev_viz/index.html")
