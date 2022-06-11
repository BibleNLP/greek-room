"""
Factory for Flask application
"""
#
# Imports
#

# Core python imports
import inspect
import logging
import logging.config
from pathlib import Path

# 3rd party imports
import flask
import flask.logging
import flask_env

# This project
import piranha_tpp_data_broker.bps.example_bp
import piranha_tpp_data_broker.bps.root_bp
import piranha_tpp_data_broker.bps.virus_total
import piranha_tpp_data_broker.bps.emr
import piranha_tpp_data_broker.bps.namebio
import piranha_tpp_data_broker.bps.hibp
#
# Module scoped variables and singletons
#

_LOGGER = logging.getLogger(__name__)


_BLUEPRINTS = [
    piranha_tpp_data_broker.bps.example_bp.BP,
    piranha_tpp_data_broker.bps.root_bp.BP,
    piranha_tpp_data_broker.bps.virus_total.BP,
    piranha_tpp_data_broker.bps.emr.BP,
    piranha_tpp_data_broker.bps.namebio.BP,
    piranha_tpp_data_broker.bps.hibp.BP,
]
"""List of blueprint singletons to load"""

#
# Helper functions for blueprint registration
#


def _is_blueprint_class(obj):
    """Predicate function used to filter for Blueprint classes during auto-registration"""
    return isinstance(obj, flask.Blueprint)


def _register_blueprints(app: flask.Flask):
    """
    Discover blueprints in this application source code and register them with the app instance.
    """
    _LOGGER.debug("Begin registering blueprints for flask app")
    assert app is not None

    for blueprint in _BLUEPRINTS:
        _LOGGER.debug("Registering blueprint from %s", str(inspect.getmodule(blueprint)))
        app.register_blueprint(blueprint)

    _LOGGER.debug("Finished registering blueprints for flask app")


#
# Configuration helpers
#

# pylint: disable=too-few-public-methods
class TwelveFactorLiteConfig(metaclass=flask_env.MetaFlaskEnv):
    """Lite flavored 12-factor app style config overrides"""

    ENV_PREFIX = ''
    ENV_LOAD_ALL = False

    PIRANHA_PY_APP_LOG_LEVEL = "debug"
    PIRANHA_PY_APP_VIRUS_TOTAL_API_KEY = ''
    PIRANHA_PY_APP_BROKER_HTTP_TIMEOUT = 5.0

    PIRANHA_PY_APP_EMR_CACHE_PATH = '/tmp/cache'
    PIRANHA_PY_APP_NAMEBIO_CACHE_PATH = '/tmp/cache'
    PIRANHA_PY_APP_HIBP_CACHE_PATH = '/tmp/cache'

    # If app should run in `test` mode
    PIRANHA_PY_APP_TEST_MODE = False

    # Directory where we store canned responses
    # to return when app is run in `test` mode
    PIRANHA_PY_APP_MOCKS_PATH = '/tmp/mocks'

def get_log_level_from_config(flask_app: flask.Flask):
    """Get the logging framework log level from a config setting in the app"""
    new_log_level = flask_app.config['PIRANHA_PY_APP_LOG_LEVEL']
    if new_log_level == 'debug':
        return logging.DEBUG
    if new_log_level == 'info':
        return logging.INFO
    if new_log_level == 'error':
        return logging.ERROR
    if new_log_level == 'fatal':
        return logging.FATAL
    if new_log_level == 'warning':
        return logging.WARNING
    raise Exception("Unsupported log level name from app config: '{}'".format(new_log_level))


#
# Flask app factory
#

def create_app():
    """
    Factory function for Flask application instances
    """

    # Instantiate app instance with some default config settings
    app = flask.Flask(__name__,
                      template_folder='templates',
                      static_folder='static')

    # Overlay the app config with the lite-12 factor app env vars
    app.config.from_object(TwelveFactorLiteConfig)

    if app.config['PIRANHA_PY_APP_TEST_MODE']:
        _LOGGER.warning("Application running in Test Mode.")

    # Create cache dirs (if not present)
    Path(app.config['PIRANHA_PY_APP_EMR_CACHE_PATH']).mkdir(parents=True, exist_ok=True)
    Path(app.config['PIRANHA_PY_APP_NAMEBIO_CACHE_PATH']).mkdir(parents=True, exist_ok=True)
    Path(app.config['PIRANHA_PY_APP_HIBP_CACHE_PATH']).mkdir(parents=True, exist_ok=True)

    # Note the final (non-secret) config settings
    _LOGGER.debug("Configured to use log level '%s'", app.config['PIRANHA_PY_APP_LOG_LEVEL'])

    # Reconfigure the root logger level based on app config
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level_from_config(app))

    # Register blueprints
    _register_blueprints(app)

    # Register/init extension singletons
    # TODO - none yet

    # Log the current rules from the app
    if _LOGGER.isEnabledFor(logging.DEBUG):
        _LOGGER.info("Routing rules:\n%s", str(app.url_map))

    # Return the app instance
    return app
