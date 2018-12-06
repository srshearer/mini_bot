#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import json
import os.path
import argparse
import requests
from flask import Flask, request, g
from mini_bot.plex_tools import plex_config
from mini_bot.plex_tools import plex_utils as plx_util
from mini_bot.plex_tools import server_utils as srv_util
from mini_bot.slack_tools.slack_utils import SlackSender

"""
Setup script:
1. Install requirements
2. Set up config file? 
   - ssh keys
   - plex token
   - local temp path
   - local final path

Notify for new local movies
- Send IMDb id and local file path to endpoint

Pull remote movies
✓ 1. Listen for notifications. Notifications include imdb id and path
✓ 2. Check local plex library for imdb id. Yes: Done. No: continue…
✓ 3. Notify, then initiate transfer from remote library to local temp directory
✓ 4. Once complete, notify and move to final location
"""


app = Flask(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description='For sending data to a server')
    parser.add_argument('-d', '--debug', dest='debug',
                        required=False, action='store_true',
                        help='Enable debug mode. Send message to test channel.')
    parser.add_argument('-i', '--guid', dest='imdb_guid', metavar='<IMDb guid>',
                        required=False, action='store',
                        help='IMDb guid to send')
    parser.add_argument('-n', '--notify', dest='notify', action='store_true',
                        help='Send new movie notification. Requires -i and -p '
                             'to be set')
    parser.add_argument('-p', '--path', dest='path', metavar='<file path>',
                        required=False, action='store',
                        help='Path to file.')
    args = parser.parse_args()

    return args


class PlexSyncer(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.debug = kwargs.get('debug', False)
        self.imdb_guid = kwargs.get('imdb_guid', None)
        self.rem_path = kwargs.get('rem_path', None)
        self.title_year = kwargs.get('title', None)
        self.movie_dir = os.path.expanduser(plex_config.NEW_MOVIE_PATH)
        self.plex_local = None

    def connect_plex(self):
        self.plex_local = plx_util.PlexSearch(
            debug=self.debug,
            auth_type=plex_config.PLEX_AUTH_TYPE,
            server=plex_config.PLEX_SERVER_URL
        )
        return

    def in_local_plex(self):
        result = self.plex_local.movie_search(self.imdb_guid)

        try:
            if plx_util.get_clean_imdb_guid(result.guid) == self.imdb_guid:
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

            file_path = srv_util.get_file(self.rem_path, self.movie_dir)
            if not file_path:
                message = 'Transfer failed: {}'.format(file_path)
            else:
                message = 'Download complete: {}'.format(file_path)
            self.notify(message)
        else:
            print('Movie already in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.rem_path))


def omdb_q(imdb_guid):
    sercher = plx_util.OmdbSearch()
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


# def after_this_request(func):
#     if not hasattr(g, 'call_after_request'):
#         g.call_after_request = []
#     g.call_after_request.append(func)
#     return func
#
#
# @app.after_request
# def per_request_callbacks(response):
#     for func in getattr(g, 'call_after_request', ()):
#         response = func(response)
#     return response
#
#
# def invalidate_username_cache():
#     @after_this_request
#     def delete_username_cookie(response):
#         response.delete_cookie('username')
#         return response

import threading


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

        thread = threading.Thread(target=sync_movie, kwargs={'syncer': syncer})
        thread.start()

    else:
        msg = 'Invalid movie'

    print(msg)
    return msg, status


def send_new_movie_notification(imdb_guid, path):
    movie_data = json.dumps(
        {
            'id': '{}'.format(imdb_guid),
            'path': '{}'.format(path)
        }
    )
    url = plex_config.REMOTE_LISTENER + '/new_movie/'
    r = requests.post(
        url, movie_data, headers={'Content-Type': 'application/json'})
    print('Response: [{}] {}'.format(r.status_code, r.text))


def main():
    args = parse_arguments()
    if args.notify:
        if not args.imdb_guid and args.path:
            print('Error: imdb_guid and path are required.')
            sys.exit(1)
        else:
            send_new_movie_notification(
                imdb_guid=args.imdb_guid, path=args.path)

    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
        # app.run(port=5000, debug=True)


if __name__ == '__main__':
    main()
