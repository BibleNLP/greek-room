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


@BP.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if flask.request.method == "POST":

        # check if the post request has the file part
        if "file" not in flask.request.files:
            flash("No file part")
            return flask.redirect(flask.url_for(".get_index"))
        file = flask.request.files["file"]

        # Validate user defined project name and language code
        project_name = sanitize_string(flask.request.form["name"])
        lang_code = sanitize_string(flask.request.form["lang-code"])
        # If the user does not select a file, the browser submits an
        # empty file without a filename. Also, check for
        # empty project name field.
        if file.filename == "" or project_name == "" or lang_code == "":
            return flask.redirect(flask.url_for(".get_index"))

        if file:
            # Save file in a new randomly named dir
            resource_id = secrets.token_urlsafe(6)
            # filename = f"{round(time.time())}_{secure_filename(file.filename)}"
            project_path = Path(flask.current_app.config["PROJECTS_PATH"]) / resource_id
            # Create the project directory
            # including any missing parents
            project_path.mkdir(parents=True)

            parsed_filepath = project_path / Path(secure_filename(file.filename))
            file.save(parsed_filepath)

            # Save metadata
            with open(f"{project_path}/metadata.json", "w") as metadata_file:
                json.dump(
                    {
                        "projectName": project_name,
                        "langCode": lang_code,
                        "wbAnalysisLastModified": datetime.now().timestamp(),
                        "projectType": "wildebeest",
                        "tags": "[]",
                        "owner": current_user.username,
                    },
                    metadata_file,
                )

            # Parse uploaded file
            parse_uploaded_files(parsed_filepath, resource_id)

    return flask.redirect(flask.url_for(".get_index"))
