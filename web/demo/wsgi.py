"""
Main WSGI entry point for the Flask application.
"""
#
# Imports
#

# This project
import web.demo.app as demo_app

#
# Singletons
#

APP = demo_app.create_app()
