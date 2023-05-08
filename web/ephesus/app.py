"""
Factory for Flask application
"""
#
# Imports
#

# Core python imports
import inspect
import logging
from functools import partial
from logging.config import dictConfig

# 3rd party imports
from sqlalchemy.event import listen
import flask

# This project
import web.ephesus.blueprints.auth
import web.ephesus.blueprints.voithos
import web.ephesus.blueprints.example
import web.ephesus.blueprints.root
import web.ephesus.blueprints.align_dev_viz
import web.ephesus.blueprints.wildebeest
from web.ephesus.exceptions import (
    AppException,
    internal_server_error,
)
from web.ephesus.extensions import (
    db,
    cache,
    email,
    login_manager,
    load_sqlite_extension,
)

#
# Module scoped variables and singletons
#

_LOGGER = logging.getLogger(__name__)
dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s] %(levelname)s %(name)s %(module)s:%(lineno)d - %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
        },
        "loggers": {"": {"level": "DEBUG", "handlers": ["wsgi"]}},
    }
)

# logging.basicConfig(level="DEBUG")

_BLUEPRINTS = [
    web.ephesus.blueprints.auth.BP,
    web.ephesus.blueprints.voithos.BP,
    web.ephesus.blueprints.example.BP,
    web.ephesus.blueprints.root.BP,
    web.ephesus.blueprints.align_dev_viz.BP,
    web.ephesus.blueprints.wildebeest.BP,
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
    app = flask.Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    app.config.from_pyfile("config.cfg")

    # Set logging level
    # if app.config["FLASK_ENV"] == "development" or app.config["DEBUG"] == "DEBUG":
    # app.logger.setLevel(logging.DEBUG)

    app.register_error_handler(AppException, internal_server_error)

    # Register blueprints
    for blueprint in _BLUEPRINTS:
        _LOGGER.debug(
            "Registering blueprint from %s", str(inspect.getmodule(blueprint))
        )
        app.register_blueprint(blueprint)

    ## Register/init extension singletons
    # Initialize the app with the SQLAlchemy extension
    db.init_app(app)

    # Load Sqlite JSON1 extension
    load_sqlite_json1_extension = partial(
        load_sqlite_extension, ext_path=app.config["SQLITE_JSON1_EXT_PATH"]
    )

    with app.app_context():
        listen(db.engine, "connect", load_sqlite_json1_extension)

    # Initialize app cache
    cache.init_app(app)

    # Create tables in DB
    with app.app_context():
        db.create_all()

    # Initialize email extension
    email.init_app(app)

    # Initialize login manager
    login_manager.init_app(app)

    # Log the current rules from the app
    if _LOGGER.isEnabledFor(logging.DEBUG):
        _LOGGER.info("Routing rules:\n%s", str(app.url_map))

    # Return the app instance
    return app
