"""
Main WSGI entry point for the Flask application.
"""
#
# Imports
#

# This project
import web.ephesus.app as ephesus_app

#
# Singletons
#

APP = ephesus_app.create_app()
