"""
Parent module for the "root" Flask blueprint.

Used to manage "root" of the path routes
"""
#
# Imports
#

# Core python imports
import logging

# 3rd party imports
import flask

# This project

#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint('root_bp',
                     __name__,
                     url_prefix='/',
                     template_folder='templates',
                     static_folder='static')

#
# Routes
#


@BP.route('/')
@BP.route('/index.html')
def get_index():
    """Get the root index for the entire app"""
    return flask.render_template('index.html')


@BP.route('/favicon.ico')
def get_favicon():
    """Provide the favicon"""
    return BP.send_static_file('favicon.ico')
