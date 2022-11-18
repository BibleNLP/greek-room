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

# 3rd party imports
import flask
from werkzeug.utils import secure_filename

# This project
from .core.preprocess import parse_usfm
from .core.wb_analyze import get_wb_analysis

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


@BP.route("/")
@BP.route("/index.html")
def get_index():
    """Get the root index for the blueprint"""
    return flask.render_template("wildebeest/index.html")


@BP.route("/upload", methods=["GET", "POST"])
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
            filename = f"{round(time.time())}_{secure_filename(file.filename)}"
            filepath = os.path.join(
                flask.current_app.config["WILDEBEEST_UPLOAD_DIR"], filename
            )
            file.save(filepath)

            # Parse uploaded USFM file
            verses, ref_id_dict = parse_usfm(filepath)

            # Run wildebeest-analysis
            analysis_results = get_wb_analysis(verses, ref_id_dict)

            return flask.render_template(
                "wildebeest/analysis.html", wb=analysis_results
            )

    return flask.redirect(flask.url_for(".get_index"))
