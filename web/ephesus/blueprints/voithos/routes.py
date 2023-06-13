"""
Parent module for the "voithos" Flask blueprint

This blueprint is a prototype of the backend for the token-level checks.
e.g. spelling, consistency and suggestions.
"""
#
# Imports
#

# Core python imports
import logging
import time
import json
import secrets
from pprint import pprint
from pathlib import Path

# 3rd party imports
import flask
from werkzeug.utils import secure_filename

# This project
from web.ephesus.common.utils import (
    sanitize_string,
    get_projects_listing,
)
from web.ephesus.common.ingester import (
    JSONDataExtractor,
    TSVDataExtractor,
    USFMDataExtractor,
)
from .core.utils import (
    parse_upload_file,
    update_file_content,
)
from .core.suggestions import get_suggestions_for_resource


#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "voithos",
    __name__,
    url_prefix="/voithos",
    template_folder="templates",
    static_folder="static",
)

#
# Routes
#

# Global variable to support versioning APIs
API_ROUTE_PREFIX = "api/v1"


@BP.route("/")
@BP.route("/index.html")
def index():
    """Get the home page for the blueprint"""
    upload_dir = Path(flask.current_app.config["VOITHOS_UPLOAD_DIR"])
    projects_listing = get_projects_listing(upload_dir)

    return flask.render_template(
        "voithos/scripture.html",
        projects_listing=projects_listing,
    )


@BP.route(f"{API_ROUTE_PREFIX}/scripture/<resource_id>", methods=["GET", "POST"])
def process_scripture(resource_id):
    """Get or set scripture content from disk"""
    if flask.request.method == "POST":
        # _LOGGER.info(flask.request.json)
        update_file_content(
            f'{Path(flask.current_app.config["VOITHOS_UPLOAD_DIR"])/Path(resource_id)/Path(resource_id)}.json',
            flask.request.json,
        )
        return {"success": True}, 200

    json_extractor = JSONDataExtractor(
        f'{Path(flask.current_app.config["VOITHOS_UPLOAD_DIR"])/Path(resource_id)}'
    )

    if flask.request.args.get("formatted") == "true":
        return flask.render_template(
            "voithos/scripture.fragment", scripture_data=json_extractor.data
        )

    return flask.jsonify(json_extractor.data)


@BP.route("/create", methods=["POST"])
def upload_file():
    if flask.request.method == "POST":

        # check if the post request has the file part
        if "file" not in flask.request.files:
            flash("No file part")
            return flask.redirect(flask.url_for(".index"))
        file = flask.request.files["file"]

        # Validate user defined project name and language code
        project_name = sanitize_string(flask.request.form["name"])
        lang_code = sanitize_string(flask.request.form["lang-code"])
        # If the user does not select a file, the browser submits an
        # empty file without a filename. Also, check for
        # empty project name field.
        if file.filename == "" or project_name == "" or lang_code == "":
            return flask.redirect(flask.url_for(".index"))

        if file:
            # Save file in a new randomly named dir
            resource_id = secrets.token_urlsafe(6)
            # filename = f"{round(time.time())}_{secure_filename(file.filename)}"
            dirpath = Path(flask.current_app.config["VOITHOS_UPLOAD_DIR"]) / Path(
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
            parse_upload_file(parsed_filepath, resource_id)

    return flask.redirect(flask.url_for(".index"))


@BP.route(f"{API_ROUTE_PREFIX}/suggestions/<resource_id>")
def get_suggestions(resource_id):
    """Get spell/consistency/prediction suggestions for the `resource_id`"""
    return (
        get_suggestions_for_resource(
            resource_id,
            flask.request.args.get("langCode"),
            flask.request.args.getlist("filter"),
        ),
        200,
    )
