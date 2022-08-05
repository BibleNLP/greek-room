"""
Factory for Flask application
"""
#
# Imports
#

# Core python imports
import inspect
import logging

# 3rd party imports
import flask

# This project
import web.demo.blueprints.word_checker
import web.demo.blueprints.example
import web.demo.blueprints.root

#
# Module scoped variables and singletons
#

_LOGGER = logging.getLogger(__name__)


_BLUEPRINTS = [
    web.demo.blueprints.word_checker.BP,
    web.demo.blueprints.example.BP,
    web.demo.blueprints.root.BP,
]
"""List of blueprint singletons to load"""


#
# Flask app factory
#


def create_app():
    """
    Factory function for Flask application instances
    """

    # Instantiate app instance with some default config settings
    app = flask.Flask(__name__, template_folder="templates", static_folder="static")

    # Register blueprints
    for blueprint in _BLUEPRINTS:
        _LOGGER.debug(
            "Registering blueprint from %s", str(inspect.getmodule(blueprint))
        )
        app.register_blueprint(blueprint)

    # Register/init extension singletons
    # TODO - none yet

    # Log the current rules from the app
    if _LOGGER.isEnabledFor(logging.DEBUG):
        _LOGGER.info("Routing rules:\n%s", str(app.url_map))

    # Return the app instance
    return app
