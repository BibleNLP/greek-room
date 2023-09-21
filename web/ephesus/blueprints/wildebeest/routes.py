"""
Parent module for the "wildebeest" Flask blueprint

"""
#
# Imports
#

# Core python imports
import logging
import os
import time
import json
import secrets
from pathlib import Path
from datetime import datetime

# 3rd party imports
import flask
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# This project
from web.ephesus.extensions import cache
from web.ephesus.constants import (
    ProjectTypes,
    LATEST_PROJECT_VERSION_NAME,
)
from web.ephesus.blueprints.auth.utils import (
    is_project_op_permitted,
)

from web.ephesus.model.common import (
    get_project_metadata,
)
from web.ephesus.blueprints.wildebeest.core.operations import (
    get_wb_analysis,
)

#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "wildebeest",
    __name__,
    url_prefix="/wildebeest",
    template_folder="templates",
    static_folder="static",
)

#
# Routes
#

# Global variable to support versioning APIs
API_ROUTE_PREFIX = "api/v1"


# @BP.route("/")
# @BP.route("/index")
# @login_required
# def get_index():
#     """Get the root index for the blueprint"""
#     projects_path = Path(flask.current_app.config["PROJECTS_PATH"])

#     # First time login
#     if not projects_path.exists():
#         projects_path.mkdir(parents=True)

#     projects_listing = get_projects_listing(
#         current_user.username,
#         projects_path,
#         roles=current_user.roles,
#         project_type=ProjectTypes.PROJ_WILDEBEEST,
#     )

#     return flask.render_template(
#         "wildebeest/index.html",
#         projects_listing=projects_listing,
#     )
#     return flask.render_template("wildebeest/index.html")


@BP.route(f"{API_ROUTE_PREFIX}/analyze/<resource_id>")
@login_required
def run_analysis(resource_id):
    """Get the Wildebeest anlysis results"""

    project_path = (
        Path(flask.current_app.config["GREEK_ROOM_PROJECTS_DIR"])
        / resource_id
        / LATEST_PROJECT_VERSION_NAME
    )

    # Verify role based permission
    if not is_project_op_permitted(current_user.username, resource_id):
        return flask.jsonify({"message": "Operation not permitted"}), 403

    vref_file_path = project_path / "vref.txt"
    vref_file_path = vref_file_path if vref_file_path.exists() else None

    # project_metadata = get_project_metadata(resource_id)
    # ## Get the last_modified_timestamp
    # analysis_last_modified = project_metadata.get("wildebeest", {}).get(
    #     "AnalysisLastModified", datetime(2001, 1, 1).timestamp()
    # )

    # data_file = (project_path / f"{resource_id}.txt")

    # if cache.get(str(data_file)) and not is_file_modified(data_file, last_modified):
    #     wb_analysis = cache.get(str(data_file))
    #     _LOGGER.debug("Using cached Wildebeest output.")

    wb_analysis, vref_dict = get_wb_analysis(
        (project_path / f"{resource_id}.txt"), resource_id, vref_file_path
    )

    if flask.request.args.get("formatted") == "true":
        return flask.render_template(
            "wildebeest/analysis.fragment",
            wb_analysis_data=wb_analysis,
            ref_id_dict=vref_dict,
        )

    return (wb_analysis, 200)
