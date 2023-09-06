"""
Parent module for the "Home" Flask blueprint.

Used to manage "Home" path routes
"""
#
# Imports
#

# Core python imports
import logging
from pathlib import Path

# 3rd party imports
import flask
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# This project
from web.ephesus.extensions import db
from web.ephesus.constants import ProjectDetails
from web.ephesus.common.utils import (
    sanitize_string,
    get_projects_listing,
)
from web.ephesus.model.user import (
    User,
    StatusType,
)

_LOGGER = logging.getLogger(__name__)


# Blueprint instance
BP = flask.Blueprint(
    "home",
    __name__,
    url_prefix="/",
    template_folder="templates",
    static_folder="static",
)

#
# Routes
#


@BP.route("/")
@BP.route("/index")
@login_required
def get_index():
    """Get the user's home page"""
    projects_listing = sorted(
        [
            ProjectDetails(
                item.project.resource_id,
                item.project.name,
                item.project.lang_code,
                item.project.create_time,
            )
            for item in current_user.projects
        ],
        reverse=True,
        key=lambda x: x.create_time,
    )

    projects_path = Path(flask.current_app.config["PROJECTS_PATH"])

    # First time login
    # if not projects_path.exists():
    #     projects_path.mkdir(parents=True)

    # projects_listing = get_projects_listing(
    #     current_user.username,
    #     projects_path,
    #     roles=current_user.roles,
    # )

    return flask.render_template(
        "home/index.html",
        projects_listing=projects_listing,
    )


@BP.route("/favicon.ico")
def get_favicon():
    """Get the app favicon"""
    return BP.send_static_file("favicon.ico")
