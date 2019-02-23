#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import json
import requests
from flask import Flask, request
from minibot import logger
from minibot.utilities import config
from minibot.utilities import plexutils
from minibot.utilities import db_utils


_NEW_MOVIE_ENDPOINT = '/new_movie/'


def validate_movie(imdb_guid, debug=False):
    logger.info('Validating movie with OMDb: {}'.format(imdb_guid))
    status, result = plexutils.omdb_guid_search(
        imdb_guid=imdb_guid, debug=debug)

    try:
        msg = '{} ({})'.format(result["Title"], result["Year"])
    except KeyError:
        msg = "Movie not found: {} - {}".format(imdb_guid, result)
        status = 404
    except Exception as e:
        msg = ('Unknown exception : {}'.format(e))

    logger.info('Result: {} - {}'.format(status, msg))

    return status, msg


def post_new_movie_to_syncer(imdb_guid, path, timeout=60):
    movie_data = json.dumps(
        {'guid': imdb_guid, 'path': path}
    )
    url = config.REMOTE_LISTENER + _NEW_MOVIE_ENDPOINT
    logger.debug('Posting request to: {}'.format(url))

    try:
        r = requests.post(
            url, movie_data,
            headers={'Content-Type': 'application/json'},
            timeout=timeout)
        logger.info('Response: [{}] {}'.format(r.status_code, r.text))

    except requests.exceptions.ConnectionError:
        logger.error('Response: [404] Server not found')

    except requests.exceptions.ReadTimeout:
        logger.error(
            '[503] Request timed out. No response after {} seconds'.format(
                timeout))


def run_server(debug=False):
    app = Flask(__name__)
    _db = db_utils.FileTransferDB()

    @app.route(_NEW_MOVIE_ENDPOINT, methods=['POST'])
    def sync_new_movie():
        r = request.get_json()
        logger.info('Request: {}'.format(r), stdout=True)

        imdb_guid = r['guid']
        remote_path = r['path']
        status, title = validate_movie(imdb_guid, debug=debug)

        if status == 200:
            msg = '[{}] {} - path: {}'.format(imdb_guid, title, remote_path)
            logger.info('Result: {} - {}'.format(status, msg))
            _db.insert(guid=imdb_guid, remote_path=remote_path)

        else:
            msg = 'Unable to locate in OMDb: {}'.format(imdb_guid)
            logger.error('{} - {}'.format(status, msg))

        return msg, status

    if debug:
        app.run(port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000)
