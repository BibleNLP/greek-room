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
from web.ephesus.constants import (
    ProjectTypes,
)
from web.ephesus.blueprints.auth.utils import (
    is_project_op_permitted,
)
from web.ephesus.common.utils import (
    sanitize_string,
    get_projects_listing,
)
from web.ephesus.blueprints.wildebeest.core.utils import (
    parse_uploaded_files,
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


@BP.route("/")
@BP.route("/index")
@login_required
def get_index():
    """Get the root index for the blueprint"""
    projects_path = Path(flask.current_app.config["PROJECTS_PATH"])

    # First time login
    if not projects_path.exists():
        projects_path.mkdir(parents=True)

    projects_listing = get_projects_listing(
        current_user.username,
        projects_path,
        roles=current_user.roles,
        project_type=ProjectTypes.PROJ_WILDEBEEST,
    )

    return flask.render_template(
        "wildebeest/index.html",
        projects_listing=projects_listing,
    )
    return flask.render_template("wildebeest/index.html")


@BP.route(f"{API_ROUTE_PREFIX}/analyze/<resource_id>")
@login_required
def run_analysis(resource_id):
    """Get the Wildebeest anlysis results"""
    resource_path = (
        Path(flask.current_app.config["PROJECTS_PATH"])
        / resource_id
        / f"{resource_id}.txt"
    )

    # Verify role based permission
    with (
        Path(flask.current_app.config["PROJECTS_PATH"]) / resource_id / "metadata.json"
    ).open("rb") as metadata_file:
        project_metadata = json.load(metadata_file)

    if not is_project_op_permitted(
        current_user.username,
        current_user.roles,
        project_metadata,
    ):
        return flask.jsonify({"message": "Operation not permitted"}), 403

    vref_file_path = (
        Path(flask.current_app.config["PROJECTS_PATH"]) / resource_id / "vref.txt"
    )
    vref_file_path = vref_file_path if vref_file_path.exists else None

    wb_analysis, vref_dict = get_wb_analysis(resource_path, vref_file_path)

    if flask.request.args.get("formatted") == "true":
        return flask.render_template(
            "wildebeest/analysis.fragment",
            wb_analysis_data=wb_analysis,
            ref_id_dict=vref_dict,
        )

    return (wb_analysis, 200)
