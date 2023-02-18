"""Define extensions for Flask app"""
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

# Create SQLAlchemy extension
db = SQLAlchemy()


# Creates and returns a cache
# instance using `cache_config`
# Create and initialize the app with the caching extension
cache_config = {
    "DEBUG": True,
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "/Users/fox/dev/workspace/bt/greek-room/web/data/cache",  # app.config["FLASK_APP_CACHE_DIR"],
    "CACHE_THRESHOLD": 100,
    "CACHE_DEFAULT_TIMEOUT": 0,  # Never expires by default
}

cache = Cache(config=cache_config)
