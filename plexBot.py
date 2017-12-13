#!/usr/bin/python -u
# encoding: utf-8

"""
Steven Shearer / srshearer@gmail.com

About:
    For interacting with a Plex server to extract information out to build a
    json message to be sent to Slack via slackAnnounce.

To do:
    - add/improve exception handling
    - improve documentation, usage, help, etc
    - find link to movie trailer
    - get token based auth working
    - add file size to notification
"""

import os
import sys
import math
import json
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '/usr/local/lib/python2.7/site-packages'))
import requests
# from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from plexBot import plex_config
from slackBot import slackAnnounce


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
    parser.add_argument('-u', '--user', dest='user', metavar='<username>',
                        required=False, action='store',
                        help='User to send the message as.')
    parser.add_argument('--serverurl', dest='plex_server_url', metavar='<url>',
                        required=False, action='store',
                        help='Override default Slack webhook url.')
    args = parser.parse_args()
    return args


class DefaultsBundle(object):
    def __init__(self):
        self.plex_server_url = plex_config.PLEX_SERVER_URL
        self.plex_server_name = plex_config.PLEX_SERVER_NAME
        self.user = plex_config.PLEX_USERNAME
        self.pw = plex_config.PLEX_PASSWORD
        self.token = plex_config.PLEX_TOKEN
        self.omdb_key = plex_config.OMDB_API_KEY
        self.maxresults = 3
        self.debug = False
        self.dryrun = False
        self.color = slackAnnounce.text_color('purple')


class SlackArgsBundle(object):
    def __init__(self, json_attachments, debug=False, dryrun=False):
        self.json_attachments = json_attachments
        self.debug = debug
        self.dryrun = dryrun


class Movie(object):
    def __init__(self, imdb_guid, movie_info_plex, movie_info_omdb, defaults):
        self.imdb_guid = imdb_guid
        self.color = defaults.color

        self.title = str(movie_info_plex.title)
        self.year = str(movie_info_plex.year)
        self.rating = str(movie_info_plex.contentRating)
        self._raw_duration = movie_info_plex.duration
        self.duration = conv_milisec_to_min(self._raw_duration)
        self.quality = get_duration(movie_info_plex)
        self.add_date = str(movie_info_plex.addedAt)
        self._media_items = movie_info_plex.media
        # self._raw_filesize = movie_info_plex.size
        # self.filesize = convert_size(self._raw_filesize)

        self.director = movie_info_omdb.director
        self.writer = movie_info_omdb.writer
        self.plot = movie_info_omdb.plot
        self.poster_link = movie_info_omdb.poster_link

    @property
    def _raw_quality(self):
        for elem in self._media_items:
            raw_quality = str(elem.videoResolution)
            self.quality = format_quality(raw_quality)
        return self.quality

    @property
    def new_movie_json_attachment(self):
        json_attachment = get_new_movie_notification_json(self)
        return json_attachment


class Omdb_Movie_Info(object):
    def __init__(self, omdb_json):
        self.data = json.loads(omdb_json)
        self.plot = self.data['Plot']
        self.poster_link = self.data['Poster']
        self.rating = self.data['Rated']
        self.director = self.data['Director']
        self.writer = self.data['Writer']
        self.revenue = self.data['BoxOffice']
        self.duration = self.data['Runtime']


def get_new_movie_notification_json(movie):
    pretext = 'New Movie Available: '
    movie_title_year = '{} ({})'.format(movie.title, movie.year)
    fallback = '{} {}'.format(pretext, movie_title_year)
    color = movie.color
    imdb_guid = movie.imdb_guid
    quality = movie.quality
    duration = movie.duration
    plot = movie.plot
    director = movie.director
    # writer = movie.writer
    # filesize = movie.filesize
    rating = movie.rating
    poster_link = movie.poster_link

    json_attachments = {
        "fallback": fallback,
        "color": color,
        "pretext": pretext,
        "title": '{} {}'.format(movie_title_year, quality),
        "title_link": 'http://www.imdb.com/title/' + imdb_guid,
        "text": duration,
        "footer": '{} \n\nDirected by: {} \nRated [{}]\n'.format(
            plot, director, rating),
        "image_url": poster_link,
    }
    return json_attachments

def querey_omdb(omdb_query_url):
    response = requests.get(omdb_query_url,
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    else:
        return response.text

def get_omdb_info(imdb_guid, omdb_key):
    omdb_querey_url = 'http://www.omdbapi.com/?i='
    omdb_querey_url = omdb_querey_url + imdb_guid + '&plot=short&apikey=' + omdb_key
    omdb_json_result = querey_omdb(omdb_querey_url)
    omdb_movie_info = Omdb_Movie_Info(omdb_json_result)
    return omdb_movie_info

def conv_milisec_to_min(miliseconds):
    s, remainder = divmod(miliseconds, 1000)
    m, s = divmod(s, 60)
    min = '{} min'.format(m)
    return min

def convert_file_size(size_bytes):
   if size_bytes == 0:
       return '0B'
   size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB')
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return '{} {}'.format(s, size_name[i])

def get_duration(movie):
    media_items = movie.media
    for elem in media_items:
        raw_quality = str(elem.videoResolution)
        quality = format_quality(raw_quality)
    if quality:
        return quality

def format_quality(raw_quality):
    input_quality = str(raw_quality)
    known_qualities = ['1080', '720', '480']
    if input_quality in known_qualities:
        quality = input_quality + 'p'
    else:
        quality = input_quality.upper()
    return str(quality)

def search_plex(plex, imdb_guid):
    movies = plex.library.section('Movies')
    found_movies = []
    for result in movies.search(guid=imdb_guid):
        found_movies.append(result)
    if len(found_movies) < 1:
        print 'Error: Could not locate movie: {}'.format(imdb_guid)
        sys.exit(1)
    for video in found_movies:
        print 'Found: {}'.format(video.title)
    return video


def main():
    defaults = DefaultsBundle()
    args = parse_arguments()

    debug, dryrun = slackAnnounce.get_debug_state(args, defaults)

    ## TOKEN BASED AUTH
    # token = defaults.token
    # baseurl = defaults.plex_server_url
    # plex = PlexServer(baseurl, token)

    # PASSWORD AUTH
    user = defaults.user
    password = defaults.pw
    servername = defaults.plex_server_name
    account = MyPlexAccount(user, password)
    plex = account.resource(servername).connect()

    imdb_guid = str(args.imdb_guid)

    movie_info_plex = search_plex(plex, imdb_guid)
    if not movie_info_plex:
        print 'Error: Could not locate movie in Plex library: ' + imdb_guid
        sys.exit(1)
    movie_info_omdb = get_omdb_info(imdb_guid, defaults.omdb_key)
    if not movie_info_omdb:
        print 'Error: Could not locate movie in omdb: ' + imdb_guid
        sys.exit(1)

    new_movie = Movie(imdb_guid, movie_info_plex, movie_info_omdb, defaults)
    json_attachments = new_movie.new_movie_json_attachment

    slack_variables = SlackArgsBundle(json_attachments, debug=debug, dryrun=dryrun)
    slack_defaults = slackAnnounce.DefaultsBundle()
    message_obj = slackAnnounce.set_slack_message(slack_variables, slack_defaults)

    slackAnnounce.post_message(message_obj)

    # movie_section = plex.library.section('Movies')
    # recently_added_movies_list = movie_section.recentlyAdded(maxresults=maxresults)
    #
    # print_info_for_results(recently_added_movies_list)

if __name__ == '__main__':
    main()