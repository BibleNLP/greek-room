"""Define extensions for Flask app"""

# 3rd Party imports
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_redmail import RedMail
from flask_login import LoginManager

## Create SQLAlchemy extension
db = SQLAlchemy()

# Sqlite extension loader
def load_sqlite_extension(db_conn, unused, ext_path=""):
    db_conn.enable_load_extension(True)
    db_conn.load_extension(ext_path)
    db_conn.enable_load_extension(False)


## Creates and returns a cache
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

## Create Email extension
email = RedMail()

## Setup app login manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"


from web.ephesus.model.user import User


@login_manager.user_loader
def user_loader(user_id):
    """flask-login user loader"""
    return User.query.get(int(user_id))
