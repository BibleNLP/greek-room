"""
Parent module for the "auth" Flask blueprint

This module provides APIs for authentication for the whole app.
"""
#
# Imports
#

# Core python imports
import logging

# 3rd party imports
import flask
from werkzeug.security import generate_password_hash, check_password_hash

# This project
from web.ephesus.extensions import db
from web.ephesus.model.user import User

#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    template_folder="templates",
    static_folder="static",
)

#
# Routes
#


@BP.route("/")
@BP.route("/login")
@BP.route("/signup")
def login():
    """Get the login page"""
    # flask.flash("Email address already exists in the system.", "signup-message")
    # flask.flash("Email address already exists in the system.", "login-message")
    return flask.render_template("auth/login-signup.html")


@BP.route("/signup", methods=["POST"])
def signup():
    """Register new user"""
    # Validate and add user to database
    email = flask.request.form.get("email")
    name = flask.request.form.get("name")
    password = flask.request.form.get("password")

    # Check if email already exists in database
    user = User.query.filter_by(email=email).first()

    # if a user is found, redirect back to signup page
    if user:
        flask.flash(
            f"The user {email} already exists in the system. Try logging in or reset password.",
            "signup-message",
        )
        return flask.redirect(flask.url_for("auth.signup"))

    # create a new user.
    # Save only password hash
    user = User(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
    )

    # Add the new user to the database
    db.session.add(user)
    db.session.commit()

    # Go to login pgae
    flask.flash(
        f"Successfully created new user.",
        "signup-message",
    )
    return flask.redirect(flask.url_for("auth.login"))


@BP.route("/logout")
@BP.route("/logout.html")
def logout():
    """Logout of the application"""
    return flask.render_template("auth/login-signup.html")
