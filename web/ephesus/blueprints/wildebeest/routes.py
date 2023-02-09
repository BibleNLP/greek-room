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

# 3rd party imports
import flask
from werkzeug.utils import secure_filename

# This project
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
def get_index():
    """Get the root index for the blueprint"""
    upload_dir = Path(flask.current_app.config["WILDEBEEST_UPLOAD_DIR"])
    projects_listing = get_projects_listing(upload_dir)

    return flask.render_template(
        "wildebeest/index.html",
        projects_listing=projects_listing,
    )
    return flask.render_template("wildebeest/index.html")


@BP.route(f"{API_ROUTE_PREFIX}/analyze/<resource_id>")
def run_analysis(resource_id):
    """Get the Wildebeest anlysis results"""
    data_path = (
        Path(flask.current_app.config["WILDEBEEST_UPLOAD_DIR"])
        / Path(resource_id)
        / Path(f"{resource_id}.txt")
    )
    wb_analysis = get_wb_analysis(data_path)

    if flask.request.args.get("formatted") == "true":
        return flask.render_template(
            "wildebeest/analysis.fragment", wb_analysis_data=wb_analysis
        )

    return (wb_analysis, 200)


@BP.route("/upload", methods=["POST"])
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
            dirpath = Path(flask.current_app.config["WILDEBEEST_UPLOAD_DIR"]) / Path(
                resource_id
            )
            dirpath.mkdir()

            # Save metadata
            with open(f"{dirpath}/metadata.json", "w") as metadata_file:
                json.dump(
                    {"projectName": project_name, "langCode": lang_code}, metadata_file
                )

            parsed_filepath = dirpath / Path(secure_filename(file.filename))
            file.save(parsed_filepath)

            # Parse uploaded file
            parse_uploaded_files(parsed_filepath, resource_id)

    return flask.redirect(flask.url_for(".get_index"))
