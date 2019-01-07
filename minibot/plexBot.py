#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import os.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import argparse
from minibot.utilities import config
from minibot.utilities import plexsyncer
from minibot.utilities import plexutils
from slackannounce.utils import SlackSender, text_color


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Send messages to slack channel. Capable of sending custom '
                    'messages, maintenance up/down messages.')
    parser.add_argument('-d', '--debug', dest='debug',
                        required=False, action='store_true',
                        help='Enable debug mode. Send message to test channel.')
    parser.add_argument('--dry', dest='dryrun',
                        required=False, action='store_true',
                        help='Enable dryrun mode. Message will not be sent.')
    parser.add_argument('-i', '--guid', dest='imdb_guid', metavar='<IMDb guid>',
                        required=False, action='store',
                        help='Find movie by IMDb guid.')
    parser.add_argument('-l', '--listen', dest='sync_listen',
                        required=False, action='store_true',
                        help='Run flask server listening for new movies at '
                             'endpoint.')
    parser.add_argument('-n', '--sync_notify', dest='sync_notify',
                        action='store_true',
                        help='Send new movie notification.Requires -i and -p '
                             'to be set')
    parser.add_argument('-p', '--path', dest='path', metavar='<file path>',
                        required=False, action='store',
                        help='Path to file.')
    args = parser.parse_args()

    return args


class MovieNotification(object):
    """Creates an object for searching a Plex server and OMDb for relevant info
    about a given movie and formatting a json notification for Slack.
    """
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False)
        self.imdb_guid = None
        self.color = text_color('purple')
        self._plex_helper = plexutils.PlexSearch(**kwargs)
        self._plex_result = None
        self._omdb_helper = plexutils.OmdbSearch(**kwargs)
        self._omdb_result = None

    def search(self, imdb_guid):
        """Searches Plex via PlexAPI and OMDb for a movie using an IMDb guid.
        Requires:
            - str(imdb_guid)
        Returns:
            - json(rich slack notification)
        """
        self.imdb_guid = imdb_guid

        self._omdb_result = self._get_omdb_info(imdb_guid)

        plex_results = self._plex_helper.movie_search(imdb_guid)
        if plex_results:
            self._plex_result = plex_results[0]
        else:
            self._plex_result = None

        return self._json_attachment

    def _get_omdb_info(self, imdb_guid):
        """Searches Plex via PlexAPI and OMDb via a query for a movie using an
        IMDb guid.
        Requires:
            - str(imdb_guid)
        Returns:
            - json.loads(OMDb query data)
        """
        omdb_result = self._omdb_helper.search(imdb_guid)
        _omdb_info_data = json.loads(omdb_result)

        return _omdb_info_data

    @property
    def _json_attachment(self):
        """Formatted json attachment suitable for sending a rich
        Slack notification.
        """
        quality = plexutils.get_video_quality(self._plex_result)
        filesize = plexutils.get_filesize(self._plex_result)

        plot = self._omdb_result['Plot']
        poster_link = self._omdb_result['Poster']
        rating = self._omdb_result['Rated']
        director = self._omdb_result['Director']
        duration = self._omdb_result['Runtime']

        pretext = 'New Movie Available:'
        movie_title_year = '{} ({})'.format(
            self._plex_result.title, self._plex_result.year)
        title = '{} {}'.format(movie_title_year, quality)
        fallback = '{} {} {}'.format(pretext, movie_title_year, quality)
        title_link = 'http://www.imdb.com/title/{}'.format(self.imdb_guid)

        json_attachments = {
            "fallback": fallback,
            "color": self.color,
            "pretext": pretext,
            "title": title,
            "title_link": title_link,
            "text": duration,
            "footer": self._format_footer(plot, director, rating, filesize),
            "image_url": poster_link,
        }

        return json_attachments

    @staticmethod
    def _format_footer(plot, director, rating, filesize):
        return '{} \n\nDirected by: {} \nRated [{}]\nSize: {}\nPoster: '.format(
            plot, director, rating, filesize)


def get_new_movie_json(imdb_guid, **kwargs):
    """Search for a movie via IMDb guid and
    assemble a json attachment for Slack"""
    movie_searcher = MovieNotification(**kwargs)
    movie_data = movie_searcher.search(imdb_guid)

    return movie_data


def send_new_movie_slack_notification(args):
    """Send a rich movie notification to Slack using supplied arguments.
    Requires:
        - str(imdb_guid)
    """
    movie_json = get_new_movie_json(
        imdb_guid=args.imdb_guid,
        debug=args.debug,
        auth_type=config.PLEX_AUTH_TYPE
    )

    slack = SlackSender(
        json_attachments=movie_json,
        debug=args.debug,
        dryrun=args.dryrun
    )

    slack.send()


def main():
    syncer = plexsyncer.PlexSyncer(imdb_guid='tt0082971', debug=True)
    print(syncer.in_local_plex())

    # args = parse_arguments()

    # if args.sync_listen:
    #     plexsyncer.run_server()
    # elif args.sync_notify:
    #     plexsyncer.send_new_movie_notification(
    #             imdb_guid=args.imdb_guid, path=args.path)
    # elif args.guid:
    #     send_new_movie_slack_notification(args)
    # else:
    #     pass


if __name__ == '__main__':
    main()
