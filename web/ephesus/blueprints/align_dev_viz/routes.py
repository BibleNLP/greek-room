"""
Parent module for the "Alignment Developer Visualization (align_dev_viz)" Flask blueprint

"""
#
# Imports
#

# Core python imports
import logging
from datetime import datetime

# 3rd party imports
import flask

# This project
from .core import filter_viz_snt_align


#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "align_dev_viz",
    __name__,
    url_prefix="/align_dev_viz",
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
    return flask.render_template("align_dev_viz/index.html")


@BP.route("<lang_pair>/<book_chapter>")
def get_chapter(lang_pair, book_chapter):
    """Return the HTML file of the 'book_chapter' for 'lang_pair'"""

    return flask.render_template(f"align_dev_viz/{lang_pair}/{book_chapter}")


@BP.route("/filter-viz-snt-align", methods=["POST"])
def search_filter():
    e_search_term = flask.request.form.get("e_search_term") or None
    f_search_term = flask.request.form.get("f_search_term") or None
    text_filename = flask.request.form.get("text_filename") or None
    html_filename_dir = flask.request.form.get("html_filename_dir") or None
    log_filename = flask.request.form.get("log_filename") or None
    e_prop = flask.request.form.get("e_prop") or None
    f_prop = flask.request.form.get("f_prop") or None
    prop_filename = flask.request.form.get("prop_filename") or None
    max_number_output_snt = (
        filter_viz_snt_align.int_or_float(
            flask.request.form.get("max_number_output_snt"), 0
        )
        or 100
    )
    auto_sample_percentage = flask.request.form.get("auto_sample")
    sample_percentage = (
        filter_viz_snt_align.int_or_float(
            flask.request.form.get("sample_percentage"), 0
        )
        or 100
    )

    e_lang_name = flask.request.form.get("e_lang_name") or None
    f_lang_name = flask.request.form.get("f_lang_name") or None

    search_results = filter_viz_snt_align.main(
        e_search_term,
        f_search_term,
        text_filename,
        html_filename_dir,
        log_filename,
        e_prop,
        f_prop,
        prop_filename,
        max_number_output_snt,
        auto_sample_percentage,
        sample_percentage,
        e_lang_name,
        f_lang_name,
    )

    return flask.render_template(
        "align_dev_viz/search_results.html",
        e_lang_name=e_lang_name,
        f_lang_name=f_lang_name,
        date=datetime.strftime(datetime.now(), "%B %d, %Y at %H:%M"),
        e_search_term=e_search_term,
        f_search_term=f_search_term,
        e_prop=e_prop,
        f_prop=f_prop,
        search_results=search_results.get("search_results_html"),
        n_matches=search_results.get("n_matches"),
        error_message=search_results.get("error_message"),
        sample_results_message=search_results.get("sample_results_message"),
    )
