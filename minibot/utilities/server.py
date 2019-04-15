#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import json
import requests
from flask import Flask, request
from utilities import config
from utilities import logger
from utilities import dbutils
from utilities import plexutils
from utilities.filesyncer import TransferQueue


_NEW_MOVIE_ENDPOINT = '/new_movie/'


def handle_movie_sync_request(raw_request, debug=False):
    request_data = {
        'title': None,
        'year': None,
        'guid': None,
        'path': None,
        'status': None,
    }

    if not raw_request['path']:
        request_data['status'] = 'No remote path for file: {}'.format(
            raw_request)
        return 400, request_data
    else:
        remote_path = raw_request['path']

    if raw_request['guid']:
        imdb_guid = raw_request['guid']
        _, result = plexutils.omdb_guid_search(imdb_guid=imdb_guid, debug=debug)
    else:
        clean_path = plexutils.get_file_path_from_string(remote_path)
        request_data['title'], request_data['year'] = plexutils.get_title_year_from_path(
            clean_path)
        status, result = plexutils.omdb_title_search(
            request_data['title'], request_data['year'])

    try:
        request_data['guid'] = result['imdbID']
        request_data['title'] = result['Title']
        request_data['year'] = result['Year']

    except KeyError as e:
        request_data['status'] = 'Movie not found: {} \n{}'.format(
            raw_request, e)
        return 404, request_data

    except Exception as e:
        request_data['status'] = 'Unknown exception: {} \n{}'.format(
            raw_request, e)
        return 400, request_data

    if not request_data['title']:
        request_data['status'] = 'Missing title: {}'.format(raw_request)
        return 404, request_data

    if not request_data['guid']:
        request_data['status'] = 'Missing guid: {}'.format(raw_request)
        return 404, request_data

    if not request_data['path']:
        request_data['status'] = 'Missing path: {}'.format(raw_request)
        return 400, request_data

    request_data['status'] = 'Success'
    return 200, request_data


def post_new_movie_to_syncer(path, imdb_guid=None, timeout=60):
    movie_info_dict = {
        'path': path,
        'guid': imdb_guid,
    }

    movie_data = json.dumps(movie_info_dict)

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
    _db = dbutils.FileTransferDB()
    q = TransferQueue(_db)

    @app.route(_NEW_MOVIE_ENDPOINT, methods=['POST'])
    def sync_new_movie():
        raw_request = request.get_json()
        logger.info('Request: {}'.format(raw_request), stdout=True)

        r_code, r = handle_movie_sync_request(raw_request, debug=debug)
        logger.debug('Result: {} - {}'.format(r_code, r))

        if r_code == 200:
            msg = '[{}] {} ({}) - path: {}'.format(
                r['guid'], r['title'], r['year'], r['path'])
            _db.insert(guid=r['guid'], remote_path=r['path'])

        else:
            msg = 'Unable to locate in OMDb: {}'.format(r['guid'])
            logger.error('{} - {}'.format(r_code, msg))

        return msg, r_code

    try:
        q.start()
        if debug:
            app.run(port=5000, debug=True)
        else:
            app.run(host='0.0.0.0', port=5000)

    except KeyboardInterrupt:
        logger.info('Stopping server and transfer queue.')

    except Exception as e:
        logger.error('Unknown exception: \n{}'.format(e))

    finally:
        logger.info('Stopping server and transfer queue')
        q.stop()
