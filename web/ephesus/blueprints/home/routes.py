"""
Parent module for the "Home" Flask blueprint.

Used to manage "Home" path routes
"""
#
# Imports
#

# Core python imports
import logging
import secrets
import shutil
from pathlib import Path
import pprint

# 3rd party imports
import flask
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# This project
from web.ephesus.extensions import db
from web.ephesus.common.utils import sanitize_string, parse_uploaded_files
from web.ephesus.constants import (
    ProjectDetails,
    LATEST_PROJECT_VERSION_NAME,
    ProjectAccessType,
)
from web.ephesus.model.user import Project, ProjectAccess

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


@BP.route("/favicon.ico")
def get_favicon():
    """Get the app favicon"""
    return BP.send_static_file("favicon.ico")


@BP.route("/")
@BP.route("/index")
@BP.route("/home")
@login_required
def get_index():
    """Get the user's home page"""
    projects_listing = sorted(
        [
            ProjectDetails(
                item.project.resource_id,
                item.project.name,
                item.project.lang_code,
                item.project.create_datetime,
            )
            for item in current_user.projects
        ],
        reverse=True,
        key=lambda x: x.create_datetime,
    )

    projects_path = Path(flask.current_app.config["PROJECTS_PATH"])

    # First time login
    # if not projects_path.exists():
    #     projects_path.mkdir(parents=True)

    return flask.render_template(
        "home/index.html",
        projects_listing=projects_listing,
    )


@BP.route("/projects/<resource_id>/overview")
@login_required
def get_project_overview(resource_id):
    """Get the basic overview of a project `resource_id`"""
    # Check if the requested project is accessible to the user
    # This returns `Project` instance as the first result
    # and the `ProjectAccess.access_type` as the second result
    # both in the same tuple.
    project_details = db.session.execute(
        (
            db.select(Project, ProjectAccess.access_type)
            .join(ProjectAccess)
            .where(ProjectAccess.user_id == current_user.id)
            .where(Project.resource_id == resource_id)
        )
    ).first()

    return flask.render_template(
        "home/project_overview.fragment",
        project=project_details,
    )


@BP.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """Handle upload of files for creating a new project"""
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

        try:
            if file:
                # Save file in a new randomly named dir
                resource_id = secrets.token_urlsafe(6)
                # filename = f"{round(time.time())}_{secure_filename(file.filename)}"
                project_path = (
                    Path(flask.current_app.config["PROJECTS_PATH"])
                    / resource_id
                    / LATEST_PROJECT_VERSION_NAME
                )
                # Create the project directory
                # including any missing parents
                project_path.mkdir(parents=True)

                parsed_filepath = project_path / Path(secure_filename(file.filename))
                file.save(parsed_filepath)

                # Parse uploaded file
                parse_uploaded_files(parsed_filepath, resource_id)

                # Add project to DB and connect with user
                project_db_instance = Project(
                    resource_id=resource_id,
                    name=project_name,
                    lang_code=lang_code,
                )
                project_access = ProjectAccess(
                    project=project_db_instance, user=current_user
                )
                project_db_instance.users.append(project_access)
                db.session.add(project_db_instance)
        except Exception as e:
            _LOGGER.error(f"Unable to create project. {e} Try again with other files.")

            # Clean-up partially created project from disk
            project_root = Path(flask.current_app.config["PROJECTS_PATH"]) / resource_id
            if project_root.is_dir():
                _LOGGER.debug("Cleaning-up partially created files from disk")
                shutil.rmtree(f"{project_root}")
                _LOGGER.debug("Done.")

            # Clean-up any partial DB transaction
            db.session.rollback()
        else:
            # Finally commit to DB if no errors
            db.session.commit()

    return flask.redirect(flask.url_for(".get_index"))
