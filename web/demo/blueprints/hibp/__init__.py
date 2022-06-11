"""
Parent module for the "hibp" (Have I Been Pwned?) Flask blueprint

Intended to provide a callout to the HIBP service
"""
#
# Imports
#

# Core python imports
import logging
import json
import requests

# 3rd party imports
import flask

# This project
from ..cache import (
    check_cache,
    write_cache,
)

#
# Singletons
#

_LOGGER = logging.getLogger(__name__)

# Blueprint instance
BP = flask.Blueprint('hibp',
                     __name__,
                     url_prefix='/hibp',
                     template_folder='templates',
                     static_folder='static')

#
# Routes
#

@BP.route('/')
@BP.route('/index.html')
def get_index():
    """Get the root index for the blueprint"""
    return flask.render_template('hibp_bp/index.html')


@BP.route('/<email_address>', methods=['GET'])
def check_hibp(email_address):
    '''
    A callout to HIBP. Caches results.
    '''
    _LOGGER.debug('Starting work to check HIBP for: %s', email_address)

    headers = flask.request.headers
    for value in ['hibp-api-key', 'user-agent']:
        if value not in headers:
            return flask.jsonify(error=f'Request is missing the header: {value}'), 500

    cache_by = email_address
    truncate_response = 'false'
    #by default we send and look up truncateResponse=false
    if flask.request.args.get('truncateResponse', 'false').lower() == 'true':
        truncate_response = 'true'
        cache_by += ' ' + truncate_response

    try:
        # check if email is cached first (account for truncateResponse parameter)
        cache_email_path, cached_resp, cached_code = \
            check_cache(flask.current_app.config['PIRANHA_PY_APP_HIBP_CACHE_PATH'], 'hibp-', cache_by)
        if cached_resp is not None:
            _LOGGER.info('Finished work by retreiving data from cache for ID: %s\n', email_address)
            return (flask.jsonify(cached_resp), cached_code)

        # If this is a test instance, skip actual API calls and return mock response
        if flask.current_app.config['PIRANHA_PY_APP_TEST_MODE']:
            _, cached_resp, _ = check_cache(flask.current_app.config['PIRANHA_PY_APP_MOCKS_PATH'], 'hibp.json', None)
            write_cache(cache_email_path, email_address, cached_resp)
            return flask.jsonify(cached_resp)

        # Regular mode of operation: proxy everything
        params = dict(flask.request.args)
        params['truncateResponse'] = truncate_response
        resp = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email_address}',
                            params=params,
                            headers={'hibp-api-key': headers['hibp-api-key'],
                                     'user-agent': headers['user-agent']},
                            timeout=5)
        try:
            resp_json = resp.json()
        except json.decoder.JSONDecodeError:
            resp_json = []
        resp_code = resp.status_code

        _LOGGER.info('Data extracted from HIBP: %s, status=%d', str(resp_json), resp_code)

        # Check if the result can be cached
        if resp_code in (requests.codes.ok, requests.codes.bad, requests.codes.not_found): #pylint: disable=no-member
            # cache results from HIBP if good/bad email/not found
            write_cache(cache_email_path, email_address, resp_json, resp_code)

        xheaders = {}
        if 'retry-after' in resp.headers:
            xheaders['retry-after'] = resp.headers['retry-after']

        _LOGGER.info('Finished work to check HIBP for ID: %s\n', email_address)
        return (flask.jsonify(resp_json), resp_code, xheaders)

    except Exception as e: #pylint: disable=broad-except
        # catch _any_ error, please
        _LOGGER.exception('Error while attempting to call HIBP and write results. %s', str(e))
        return flask.jsonify(error='Application error. Unable to process request. Try again.'), 500
