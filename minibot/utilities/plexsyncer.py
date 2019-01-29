#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import os.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import requests
import threading
from flask import Flask, request #, g
from minibot.utilities import config
from minibot.utilities import utils
from minibot.utilities import plexutils
from minibot.utilities import serverutils
from slackannounce.utils import SlackSender


logger = utils.Logger(file_path=os.path.abspath('./plexbot.log'), stdout=True)
_NEW_MOVIE_ENDPOINT = '/new_movie/'

class PlexSyncer(object):
    def __init__(self, imdb_guid=None, rem_path=None, debug=False, **kwargs):
        self.kwargs = kwargs
        self.debug = debug
        self.imdb_guid = imdb_guid
        self.rem_path = rem_path
        self.title_year = kwargs.get('title', None)
        self.movie_dir = os.path.expanduser(config.NEW_MOVIE_PATH)
        self.plex_local = None

    def connect_plex(self):
        logger.info('Connecting to Plex')
        self.plex_local = plexutils.PlexSearch(
            debug=self.debug,
            auth_type=config.PLEX_AUTH_TYPE,
            server=config.PLEX_SERVER_URL
        )
        self.plex_local.connect()

        return

    def in_local_plex(self):
        import pdb; pdb.set_trace()
        _, self.title_year = validate_movie(self.imdb_guid)
        title, year = self.title_year.replace(')', '').split(' (')
        logger.info('Checking local Plex for: [{}][{}][{}]'.format(
            self.imdb_guid, title, year))

        if not self.plex_local:
            self.connect_plex()

        results = self.plex_local.movie_search(
            guid=self.imdb_guid, title=title, year=year)

        if not results:
            return False
        else:
            try:
                formatted_results = ['Found: ']
                for r in results:
                    formatted = '\t{} - {} ({})'.format(
                        plexutils.get_clean_imdb_guid(r.guid), r.title, r.year)
                    formatted_results.append(formatted)

                logger.debug('\n'.join(formatted_results))  # ToDo: Remove debug lines

                return True

            except Exception as e:
                logger.error('Error checking local Plex server: {}'.format(e))

        return False

    def notify_slack(self, message, room='me'):
        logger.info(message)
        notification = SlackSender(room=room, debug=self.debug)
        notification.set_simple_message(
            message=message, title='Plex Syncer Notification')
        notification.send()

    def run_sync_flow(self):
        self.connect_plex()
        if not self.in_local_plex():
            message = 'Movie not in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path)
            logger.info(message)
            self.notify_slack(message)

            file_path, message, success = serverutils.get_file(
                self.rem_path, self.movie_dir)
            if not file_path or not success:
                message = 'Transfer failed: {}'.format(message)
                logger.error(message)
            else:
                message = 'Download complete: {}\n\t- {}'.format(
                    message, file_path)
                logger.info(message)
            self.notify_slack(message)
        else:
            logger.info('Movie already in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path))


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


def post_new_movie_to_syncer(imdb_guid, path):
    movie_data = json.dumps(
        {'id': imdb_guid, 'path': path}
    )
    url = config.REMOTE_LISTENER + _NEW_MOVIE_ENDPOINT
    logger.debug('Posting request to: {}'.format(url))

    try:
        r = requests.post(
            url, movie_data, headers={'Content-Type': 'application/json'})
        logger.info('Response: [{}] {}'.format(r.status_code, r.text))

    except requests.exceptions.ConnectionError:
        logger.error('Response: [404] Server not found')


def run_server(debug=False):
    app = Flask(__name__)

    @app.route(_NEW_MOVIE_ENDPOINT, methods=['POST'])
    def sync_new_movie():

        def sync_movie(syncer):
            syncer.run_sync_flow()

        r = request.get_json()
        logger.info('Request: {}'.format(r), stdout=True)

        imdb_guid = r["id"]
        path = r["path"]
        status, title = validate_movie(imdb_guid, debug=debug)

        if status == 200:
            msg = '[{}] {} - path: {}'.format(imdb_guid, title, path)
            logger.info('Result: {} - {}'.format(status, msg))
            syncer = PlexSyncer(
                imdb_guid=imdb_guid,
                rem_path=path,
                title=title
            )

            thread = threading.Thread(target=sync_movie,
                                      kwargs={'syncer': syncer})
            thread.start()

        else:
            msg = 'Unable to locate in OMDb: {}'.format(imdb_guid)
            logger.error('{} - {}'.format(status, msg))

        return msg, status

    if debug:
        app.run(port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000)
