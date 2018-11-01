#!/usr/bin/python -u
# encoding: utf-8

"""
Version: 2.0
Steven Shearer / srshearer@gmail.com

About:
    Utilizes plexUtils to search for movies in Plex and OMDb, extract
    information about the movie, and format it into json to send as
    a rich Slack message/
"""

import sys
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '/usr/local/lib/python2.7/site-packages'))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import argparse
import plexBot.plex_config as config
import plexBot.plexUtils as pu
from plexBot.plexUtils import PlexSearch, OmdbSearch
from slackBot.slackUtils import SlackSender, text_color


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
                        required=True, action='store',
                        help='Find movie by IMDb guid.')
    args = parser.parse_args()

    return args


class MovieNotification(object):
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False)
        self.imdb_guid = None
        self.color = text_color('purple')
        self._plex_helper = PlexSearch(**kwargs)
        self._plex_result = None
        self._omdb_helper = OmdbSearch(**kwargs)
        self._omdb_result = None

    def search(self, imdb_guid):
        self.imdb_guid = imdb_guid
        self._plex_result = self._plex_helper.movie_search(imdb_guid)
        self._omdb_result = self._get_omdb_info(imdb_guid)

        return self.json_attachment

    def _get_omdb_info(self, imdb_guid):
        omdb_result = self._omdb_helper.search(imdb_guid)
        _omdb_info_data = json.loads(omdb_result)

        return _omdb_info_data

    @property
    def json_attachment(self):
        quality = pu.get_video_quality(self._plex_result)
        filesize = pu.get_filesize(self._plex_result)

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
    movie_searcher = MovieNotification(**kwargs)
    movie_data = movie_searcher.search(imdb_guid)

    return movie_data


def send_movie_notification(args):
    movie_json = get_new_movie_json(
        imdb_guid=args.imdb_guid,
        debug=args.debug,
        con_type=config.PLEX_CON_TYPE
    )

    slack = SlackSender(
        json_attachments=movie_json,
        debug=args.debug,
        dryrun=args.dryrun
    )

    slack.send()


def main():
    args = parse_arguments()
    send_movie_notification(args)


if __name__ == '__main__':
    main()
