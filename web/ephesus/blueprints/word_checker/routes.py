"""
Parent module for the "spell checker" Flask blueprint

This blueprint is a prototype of the backend for the word-level checks.
e.g. spellings and word suggestions.
"""
#
# Imports
#

# Core python imports
import logging
import time
import secrets
from pprint import pprint
from pathlib import Path

# 3rd party imports
import flask
from werkzeug.utils import secure_filename

# This project
from .core.utils import (
    JSONDataExtractor,
    TSVDataExtractor,
    USFMDataExtractor,
    parse_input,
    update_file_content,
)
from .core.spell_checker import get_suggestions_for_resource


#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "word_checker",
    __name__,
    url_prefix="/word_checker",
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
def get_index():
    """Get the root index for the blueprint"""
    tsv_extractor = TSVDataExtractor(f'{flask.current_app.config["DATA_PATH"]}/en_ult')
    return flask.render_template(
        "word_checker/index.html", scripture_data=tsv_extractor.data
    )


@BP.route("/home")
def get_home():
    """Get the home page for the blueprint"""
    upload_dir = Path(flask.current_app.config["WORD_CHECKER_UPLOAD_DIR"])
    listing = [
        (entry.name, entry.stat().st_birthtime)
        for entry in upload_dir.iterdir()
        if not entry.name.startswith(".")
    ]
    listing = [item[0] for item in sorted(listing, reverse=True, key=lambda x: x[1])]

    tsv_extractor = TSVDataExtractor(f'{flask.current_app.config["DATA_PATH"]}/en_ult')
    return flask.render_template(
        "word_checker/scripture.html",
        scripture_data=tsv_extractor.data,
        listing=listing,
    )


@BP.route(f"{API_ROUTE_PREFIX}/scripture/<resource_id>", methods=["GET", "POST"])
def process_scripture(resource_id):
    """Get or set scripture content from disk"""
    if flask.request.method == "POST":
        # _LOGGER.info(flask.request.json)
        update_file_content(
            f'{Path(flask.current_app.config["WORD_CHECKER_UPLOAD_DIR"])/Path(resource_id)/Path(resource_id)}.json',
            flask.request.json,
        )
        return {"success": True}, 200

    json_extractor = JSONDataExtractor(
        f'{Path(flask.current_app.config["WORD_CHECKER_UPLOAD_DIR"])/Path(resource_id)}'
    )

    if flask.request.args.get("formatted") == "true":
        return flask.render_template(
            "word_checker/scripture.fragment", scripture_data=json_extractor.data
        )

    return flask.jsonify(json_extractor.data)


@BP.route("/upload", methods=["POST"])
def upload_file():
    if flask.request.method == "POST":

        # check if the post request has the file part
        if "file" not in flask.request.files:
            flash("No file part")
            return flask.redirect(flask.request.url)
        file = flask.request.files["file"]

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            return flask.redirect(flask.request.url)
        if file:
            # Save file in a new randomly named dir
            resource_id = secrets.token_urlsafe(6)
            # filename = f"{round(time.time())}_{secure_filename(file.filename)}"
            dirpath = Path(flask.current_app.config["WORD_CHECKER_UPLOAD_DIR"]) / Path(
                resource_id
            )
            dirpath.mkdir()

            filepath = dirpath / Path(secure_filename(file.filename))
            file.save(filepath)

            # Parse uploaded file
            parse_input(filepath, resource_id)

    return flask.redirect(flask.url_for(".get_home"))


@BP.route(
    f"{API_ROUTE_PREFIX}/suggestions/<resource_id>",
    defaults={"book": None, "chapter": None, "verse": None},
)
@BP.route(
    f"{API_ROUTE_PREFIX}/suggestions/<resource_id>/<book>",
    defaults={"chapter": None, "verse": None},
)
@BP.route(
    f"{API_ROUTE_PREFIX}/suggestions/<resource_id>/<book>/<chapter>",
    defaults={"verse": None},
)
@BP.route(f"{API_ROUTE_PREFIX}/suggestions/<resource_id>/<book>/<chapter>/<verse>")
def get_suggestions(resource_id, book, chapter, verse):
    """Get spell/consistency/prediction suggestions for the `resource_id`"""
    return get_suggestions_for_resource(resource_id, book, chapter, verse), 200
