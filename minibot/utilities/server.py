#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import os.path
import json
import requests
import sqlite3
from flask import Flask, request
from utilities import config
from utilities import logger
from utilities import dbutils
from utilities import omdb
from utilities import plexutils
from utilities.utils import retry
from utilities.utils import SigInt
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
        request_data['path'] = raw_request['path']

    _omdb = omdb.OMDb(api_key=config.OMDB_API_KEY, debug=debug)

    if raw_request['guid']:
        imdb_guid = raw_request['guid']
        omdb_status, result = _omdb.search(imdb_guid=imdb_guid)
    else:
        clean_path = os.path.basename(request_data['path'])
        request_data['title'], request_data['year'] = plexutils.get_title_year_from_path(
            clean_path)
        omdb_status, result = _omdb.search(
            title=request_data['title'], year=request_data['year'])

    if not omdb_status == 200:
        request_data['status'] = 'Error locating movie in OMDB: {}'.format(
            raw_request)
        return omdb_status, request_data

    try:
        if not result['Type']:
            request_data['status'] = 'Unable to determine content type: ' \
                                     '{}'.format(raw_request)
            return 415, request_data

        if not result['Type'] == 'movie':
            request_data['status'] = 'Content type is not movie: {} | {}'.format(
                result['Type'], raw_request)
            return 415, request_data

    except TypeError:
        request_data['status'] = 'Unable to determine content type: {}'.format(
            raw_request)
        return 415, request_data

    try:
        request_data['guid'] = result['imdbID']
        request_data['title'] = result['Title']
        request_data['year'] = result['Year']

    except KeyError as e:
        request_data['status'] = 'Movie not found: {} | {}'.format(
            raw_request, e)
        return 404, request_data

    except Exception as e:
        request_data['status'] = 'Unknown exception: {} | {}'.format(
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
    logger.debug('Posting request to: {} - {}'.format(url, movie_data))

    try:
        r = requests.post(
            url, movie_data,
            headers={'Content-Type': 'application/json'},
            timeout=timeout
        )
        logger.info('Response: [{}] {}'.format(r.status_code, r.text))

    except requests.exceptions.ConnectionError:
        logger.error('Response: [404] Server not found')

    except requests.exceptions.ReadTimeout:
        logger.error(
            '[503] Request timed out. No response after {} seconds'.format(
                timeout))


@retry(delay=3, logger=logger)
def run_server(debug=False):
    app = Flask(__name__)
    _db = dbutils.FileTransferDB()
    logger.debug('db exists?: {} | {}'.format(
        os.path.exists(_db.db_path), _db.db_path))
    q = TransferQueue(_db)

    @app.route(_NEW_MOVIE_ENDPOINT, methods=['POST'])
    def sync_new_movie():
        raw_request = request.get_json()
        logger.info('Request: {}'.format(raw_request), stdout=True)

        r_code, r = handle_movie_sync_request(raw_request, debug=debug)
        logger.debug('Result: {} - {}'.format(r_code, r))

        if r_code == 200:
            try:
                if debug:
                    logger.debug('Inserting into db: {} / {} \n{}'.format(
                        r['guid'], r['path'], r))
                _db.insert(guid=r['guid'], remote_path=r['path'])
            except sqlite3.IntegrityError as e:
                if 'UNIQUE constraint failed' in e.message:
                    logger.warning('Skipping request. Already in '
                                   'database: {}'.format(r['guid']))
                    r_code = 208
                    r['status'] = 'Item already requested'
            except Exception as e:
                logger.error('Exception in db insert time: \n{}\n\n'.format(e))
                raise

        else:
            logger.warning('{} - {}'.format(r_code, r['status']))

        return r['status'], r_code

    try:
        logger.debug('starting queue')
        q.start()
        if debug:
            app.run(port=5000, debug=True)
        else:
            app.run(host='0.0.0.0', port=5000)

    except SigInt:
        logger.info('Exiting...\t(SigInt)')

    except KeyboardInterrupt:
        logger.info('Exiting...\t(Keyboard interrupt)')

    except Exception as e:
        logger.error('Unknown exception: \n{}'.format(e))

    finally:
        logger.info('Stopping server and transfer queue')
        q.stop()
