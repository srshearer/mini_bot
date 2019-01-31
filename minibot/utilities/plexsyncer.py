#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import os.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import requests
import threading
from flask import Flask, request
from minibot.utilities import config
from minibot.utilities import utils
from minibot.utilities import plexutils
from minibot.utilities import serverutils
from slackannounce.utils import SlackSender


logger = utils.Logger(file_path=os.path.abspath('./plexbot.log'), stdout=True)
_NEW_MOVIE_ENDPOINT = '/new_movie/'


class PlexSyncer(object):
    def __init__(self, imdb_guid=None, rem_path=None, debug=False,
                 logger=logger, **kwargs):
        self.kwargs = kwargs
        self.debug = debug
        self.imdb_guid = imdb_guid
        self.rem_path = rem_path
        self.title_year = kwargs.get(str('title'), None)
        self.movie_dir = os.path.expanduser(config.FILE_TRANSFER_COMPLETE_DIR)
        self.plex_local = None
        self.logger = logger

    def connect_plex(self):
        logger.info('Connecting to Plex')
        self.plex_local = plexutils.PlexSearch(
            debug=self.debug,
            auth_type=config.PLEX_AUTH_TYPE,
            server=config.PLEX_SERVER_URL
        )
        self.plex_local.connect()

        return

    def notify_slack(self, message, room='me'):
        self.logger.info(message)
        notification = SlackSender(room=room, debug=self.debug)
        notification.set_simple_message(
            message=message, title='Plex Syncer Notification')
        notification.send()

    def run_sync_flow(self):
        self.connect_plex()
        if not self.plex_local.in_plex_library(guid=self.imdb_guid):
            message = 'Movie not in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path)
            self.logger.info(message)
            self.notify_slack(message)

            syncer = serverutils.FileSyncer(
                remote_file=self.rem_path,
                destination=self.movie_dir,
                logger=logger)
            success, file_path = syncer.get_remote_file()

            if not file_path or not success:
                message = 'Transfer failed: {}'.format(message)
                self.logger.error(message)
            else:
                message = 'Download complete: {}\n\t- {}'.format(
                    message, file_path)
                self.logger.info(message)
            self.notify_slack(message)
        else:
            self.logger.info('Movie already in library: [{}] {} - {}'.format(
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


def run_server(debug=False, logger=logger):
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
                title=title,
                logger=logger
            )

            thread = threading.Thread(target=sync_movie,
                                      kwargs={str('syncer'): syncer})
            thread.start()

        else:
            msg = 'Unable to locate in OMDb: {}'.format(imdb_guid)
            logger.error('{} - {}'.format(status, msg))

        return msg, status

    if debug:
        app.run(port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000)
