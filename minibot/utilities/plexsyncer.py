#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import os.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import argparse
import requests
import threading
from flask import Flask, request #, g
from minibot.utilities import config
from minibot.utilities import plexutils
from minibot.utilities import serverutils
from slackannounce.utils import SlackSender


class PlexSyncer(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.debug = kwargs.get('debug', False)
        self.imdb_guid = kwargs.get('imdb_guid', None)
        self.rem_path = kwargs.get('rem_path', None)
        self.title_year = kwargs.get('title', None)
        self.movie_dir = os.path.expanduser(config.NEW_MOVIE_PATH)
        self.plex_local = None

    def connect_plex(self):
        self.plex_local = plexutils.PlexSearch(
            debug=self.debug,
            auth_type=config.PLEX_AUTH_TYPE,
            server=config.PLEX_SERVER_URL
        )
        return

    def in_local_plex(self):
        result = self.plex_local.movie_search(self.imdb_guid)

        try:
            if plexutils.get_clean_imdb_guid(result.guid) == self.imdb_guid:
                print('Found in local plex: {} ({})'.format(result.title, result.year)) # ToDo: Remove debug line
                return True
        except AttributeError:
            pass
        except Exception as e:
            print('Error checking local Plex server: {}'.format(e))

        return False

    def notify(self, message):
        print(message)
        notification = SlackSender(room='me', debug=self.debug)
        notification.set_simple_message(
            message=message, title='Plex Syncer Notification')
        notification.send()

    def run_sync_flow(self):
        self.connect_plex()
        if not self.in_local_plex():
            message = 'Movie not in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path)
            self.notify(message)
            print('rem_path: {} / movie_dir: {}'.format(self.rem_path, self.movie_dir)) # ToDo: Remove debug line

            file_path = serverutils.get_file(self.rem_path, self.movie_dir)
            if not file_path:
                message = 'Transfer failed: {}'.format(file_path)
            else:
                message = 'Download complete: {}'.format(file_path)
            self.notify(message)
        else:
            print('Movie already in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path))


def omdb_q(imdb_guid):
    sercher = plexutils.OmdbSearch()
    result = json.loads(sercher.search(imdb_guid=imdb_guid))

    try:
        msg = '{} ({})'.format(result["Title"], result["Year"])
        status = 200
    except KeyError:
        msg = "Movie not found: {} - {}".format(imdb_guid, result)
        status = 404
    except Exception as e:
        msg = ('Movie not found. Unknown error: {}'.format(e))
        status = 404

    return msg, status


def send_new_movie_notification(imdb_guid, path):
    movie_data = json.dumps(
        {'id': imdb_guid, 'path': path}
    )
    url = config.REMOTE_LISTENER + '/new_movie/'

    try:
        r = requests.post(
            url, movie_data, headers={'Content-Type': 'application/json'})
        print('Response: [{}] {}'.format(r.status_code, r.text))

    except requests.exceptions.ConnectionError:
        print('Response: [404] Server not found')
        sys.exit(1)


def run_server():
    app = Flask(__name__)

    @app.route('/new_movie/', methods=['POST'])
    def sync_new_movie():

        def sync_movie(syncer):
            syncer.run_sync_flow()

        r = request.get_json()
        print(r)
        imdb_guid = r["id"]
        path = r["path"]
        title, status = omdb_q(imdb_guid)

        if status == 200:
            msg = '[{}] {} - path: {}'.format(imdb_guid, title, path)
            syncer = PlexSyncer(
                imdb_guid=imdb_guid,
                rem_path=path,
                title=title
            )

            thread = threading.Thread(target=sync_movie,
                                      kwargs={'syncer': syncer})
            thread.start()

        else:
            msg = 'Invalid movie'

        print(msg)
        return msg, status

    app.run(host='0.0.0.0', port=5000, debug=True)
