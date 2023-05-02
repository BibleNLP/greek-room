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
from flask_login import (
    login_user,
    logout_user,
    login_required,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

# This project
from web.ephesus.blueprints.auth.utils import (
    is_valid_username,
    is_valid_password,
)
from web.ephesus.extensions import db, email as email_handler, cache
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
@BP.route("/signup")
@BP.route("/login")
def login():
    """Get the login page"""
    # flask.flash("Email address already exists in the system.", "signup-message-fail")
    # flask.flash("Email address already exists in the system.", "login-message-success")
    return flask.render_template("auth/login-signup.html")


@BP.route("/login", methods=["POST"])
def login_submit():
    # Get form values
    login_id = flask.request.form.get("loginId")
    password = flask.request.form.get("password")
    is_remember_me = True if flask.request.form.get("remember-me") else False

    # Check login_id against usernames
    user = User.query.filter(
        (db.func.upper(User.email) == db.func.upper(login_id))
        | (db.func.upper(User.username) == db.func.upper(login_id))
    ).first()

    # Check for login failure
    if not user or not check_password_hash(user.password, password):
        flask.flash(
            f"Invalid username or password. Please Try again.",
            "login-message-fail",
        )
        return flask.redirect(flask.url_for("auth.login"))

    # Check if user has their email address verified
    if user and not user.is_email_verified:
        flask.flash(
            f"Please verify your email address before attempting to login. We sent a message to the email on file with a link (check spam folder too).",
            "login-message-fail",
        )
        # Send verification email
        email_handler.send(
            subject="Greek Room: Verify your email",
            receivers=email,
            html_template="auth/verify-email.html",
            body_params={"token": user.get_email_verification_token()},
        )
        return flask.redirect(flask.url_for("auth.login"))

    # Successfully logged-in
    login_user(user, remember=is_remember_me)
    return flask.redirect(flask.url_for("wildebeest.get_index"))


@BP.route("/signup", methods=["POST"])
def signup():
    """Register new user"""
    # Validate and add user to database
    email = flask.request.form.get("email")
    username = flask.request.form.get("username").lower()
    password = flask.request.form.get("password")

    # Basic validation
    if not is_valid_username(username) or not is_valid_password(password):
        flask.flash(
            f"Invalid username or password. Please try again.",
            "signup-message-fail",
        )
        return flask.redirect(flask.url_for("auth.signup"))

    # Check if email already exists in database
    user = User.query.filter(db.func.upper(User.email) == db.func.upper(email)).first()

    # if a user is found, redirect back to signup page
    if user:
        flask.flash(
            f"This user already exists in the system. Try logging in or reset password.",
            "signup-message-fail",
        )
        return flask.redirect(flask.url_for("auth.signup"))

    # create a new user.
    # Save only password hash
    # See https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#pbkdf2
    user = User(
        email=email,
        username=username,
        password=generate_password_hash(password, method="pbkdf2:sha512:210000"),
    )

    # Add the new user to the database
    db.session.add(user)
    db.session.commit()

    # Send verification email
    email_handler.send(
        subject="Greek Room: Verify your email",
        receivers=email,
        html_template="auth/verify-email.html",
        body_params={"token": user.get_email_verification_token()},
    )

    # Go to login pgae
    flask.flash(
        f"Successfully created new user. Please verify your email address before attempting to login.",
        "signup-message-success",
    )
    return flask.redirect(flask.url_for("auth.login"))


@BP.route("/logout")
@BP.route("/logout.html")
@login_required
def logout():
    """Logout of the application"""
    logout_user()
    return flask.redirect(flask.url_for("auth.login"))


@BP.route("/request-reset-password", methods=["POST"])
def request_reset_password():
    """Email link for reset password"""
    if flask.request.method == "POST":
        login_id = flask.request.form.get("reset-password-loginId")
        # Check login_id against usernames
        user = User.query.filter(
            (db.func.upper(User.email) == db.func.upper(login_id))
            | (db.func.upper(User.username) == db.func.upper(login_id))
        ).first()

        if not user:
            flask.flash(
                f"We were not able to find this user. Please enter an existing username or email address to reset password.",
                "login-message-fail",
            )
            return flask.redirect(flask.url_for("auth.login"))

        if user:
            # Send verification email
            email_handler.send(
                subject="Greek Room: Reset Password",
                receivers=user.email,
                html_template="auth/reset-password-email.html",
                body_params={"token": user.get_reset_password_token()},
            )
            flask.flash(
                f"We have sent a message to the email address on file with a link with which you can reset your password (check spam folder too).",
                "login-message-success",
            )
            return flask.redirect(flask.url_for("auth.login"))


@BP.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Handle reset password"""
    if flask.request.method == "GET":
        token = flask.request.args.get("token")

        # Invalid/expired token
        email = User.decrypt_email_token(token, salt="reset-password")
        if not email:
            flask.flash(
                f"Invalid or expired link. Please try password reset again.",
                "login-message-fail",
            )
            return flask.redirect(flask.url_for("auth.login"))

        return flask.render_template(
            "auth/reset-password.html", token=token if token else ""
        )

    if flask.request.method == "POST":
        token = flask.request.form.get("token")
        password = flask.request.form.get("password")
        email = User.decrypt_email_token(token, salt="reset-password")

        # Invalid/expired token
        if not email:
            flask.flash(
                f"Invalid or expired link. Please try password reset again.",
                "login-message-fail",
            )
            return flask.redirect(flask.url_for("auth.login"))

        # Basic validation
        if not is_valid_password(password):
            flask.flash(
                f"Invalid password. Please try again.",
                "reset-password-message-fail",
            )
            return flask.redirect(flask.url_for("auth.reset_password", token=token))

        # If valid token and corresponding user
        if email:
            user = User.query.filter(
                db.func.upper(User.email) == db.func.upper(email)
            ).first()
            _LOGGER.debug(user)

            # If user is not verified, do that first
            if not user.is_email_verified:
                # Send verification email
                email_handler.send(
                    subject="Greek Room: Verify your email",
                    receivers=email,
                    html_template="auth/verify-email.html",
                    body_params={"token": user.get_email_verification_token()},
                )
                flask.flash(
                    f"Please verify your account first. We just sent a message to '{user.email}' (check spam folder too).",
                    "reset-password-message-fail",
                )
                return flask.redirect(flask.url_for("auth.reset_password"))

            # User is verified and exists
            # update password hash in DB
            user.password = generate_password_hash(
                password, method="pbkdf2:sha512:210000"
            )
            db.session.commit()

            flask.flash(
                f"Successfully reset password for {user.username}. Login to continue.",
                "login-message-success",
            )
            return flask.redirect(flask.url_for("auth.login"))

        return flask.redirect(flask.url_for("auth.reset_password", token=token))


@BP.route("/verify-email/<token>")
def verify_email(token):
    """Verify token for newly signed-up users"""
    email = User.decrypt_email_token(token, salt="email-verification")
    if email:
        user = User.query.filter(
            db.func.upper(User.email) == db.func.upper(email)
        ).first()
        user.is_email_verified = True
        db.session.add(user)
        db.session.commit()
        flask.flash(
            f"Thank you for verifying your email! Please login to continue.",
            "login-message-success",
        )
        return flask.redirect(flask.url_for("auth.login"))

    flask.flash(
        f"Invalid or expired registration token. Try logging-in again to receive another verification email.",
        "login-message-fail",
    )
    return flask.redirect(url_for("auth.login"))


@BP.route("/username/<username>")
def is_username_exists(username):
    """Return boolean based on existence of username in Database"""
    user = User.query.filter(
        db.func.lower(User.username) == db.func.lower(username)
    ).first()
    return flask.jsonify({"username": username, "exists": True if user else False})
