#!/usr/bin/python -u
# encoding: utf-8

"""
Version: 1.1
Steven Shearer / srshearer@gmail.com

About:
    For interacting with a Plex server to extract information out to build a
    json message to be sent to Slack via slackAnnounce.

To do:
    - add/improve exception handling
    - improve documentation, usage, help, etc
    - get token based auth working
    - verify movie search results were actually added to Plex recently
"""

import os
import sys
import re
import math
import json
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '/usr/local/lib/python2.7/site-packages'))
import requests
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
    args = parser.parse_args()
    return args


class DefaultsBundle(object):
    def __init__(self):
        self.plex_server_url = plex_config.PLEX_SERVER_URL
        self.plex_server_name = plex_config.PLEX_SERVER_NAME
        self.plex_user = plex_config.PLEX_USERNAME
        self.plex_pw = plex_config.PLEX_PASSWORD
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
    def __init__(self, movie_info_plex, defaults):
        self.imdb_guid = get_clean_imdb_guid(movie_info_plex.guid)
        self.color = defaults.color

        self.title = str(movie_info_plex.title)
        self.year = str(movie_info_plex.year)
        self.rating = str(movie_info_plex.contentRating)
        self._raw_duration = movie_info_plex.duration
        self.duration = conv_milisec_to_min(self._raw_duration)
        self.quality = get_video_quality(movie_info_plex)
        self.filesize = get_filesize(movie_info_plex)
        self._media_items = movie_info_plex.media

        self._omdb_json = self._get_omdb_info(self.imdb_guid, defaults.omdb_key)
        self.plot = self._omdb_json['Plot']
        self.poster_link = self._omdb_json['Poster']
        self.rating = self._omdb_json['Rated']
        self.director = self._omdb_json['Director']
        self.writer = self._omdb_json['Writer']
        self.revenue = self._omdb_json['BoxOffice']
        self.duration = self._omdb_json['Runtime']

    def _get_omdb_info(self, imdb_guid, omdb_key):
        _omdb_info_json = get_omdb_info(imdb_guid, omdb_key)
        print _omdb_info_json
        _omdb_info_data = json.loads(_omdb_info_json)
        print _omdb_info_data
        return _omdb_info_data

    @property
    def json_attachment(self):
        json_attachment = get_movie_notification_json(self)
        return json_attachment


def get_movie_notification_json(movie):
    pretext = 'New Movie Available: '
    movie_title_year = '{} ({})'.format(movie.title, movie.year)
    fallback = '{} {}'.format(pretext, movie_title_year)
    color = movie.color
    imdb_guid = movie.imdb_guid
    quality = movie.quality
    duration = movie.duration
    plot = movie.plot
    director = movie.director
    rating = movie.rating
    poster_link = movie.poster_link
    filesize = movie.filesize

    json_attachments = {
        "fallback": fallback,
        "color": color,
        "pretext": pretext,
        "title": '{} {}'.format(movie_title_year, quality),
        "title_link": 'http://www.imdb.com/title/' + imdb_guid,
        "text": duration,
        "footer": '{} \n\nDirected by: {} \nRated [{}]\nSize: {}\nPoster: '.format(
            plot, director, rating, filesize),
        "image_url": poster_link,
    }
    return json_attachments

def get_server_instance(defaults):
    """Uses PlexAPI to instansiate a Plex server connection.
    Requires a Defaults object with…
        - Plex username: Defaults.plex_user
        - Plex password: Defaults.plex_pw
        - Plex server name: Defaults.plex_server_name
    """
    user = defaults.plex_user
    password = defaults.plex_pw
    servername = defaults.plex_server_name
    account = MyPlexAccount(user, password)
    plex = account.resource(servername).connect()
    return plex

def search_plex(plex, imdb_guid):
    """Uses PlexAPI to search for a movie via IMDb guid.
    Requires:
        - plex server instance object
        - IMDb guid of a movie to search for
    Returns a video object.
    """
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

def querey_omdb(omdb_query_url):
    """Generic function to query a url via requests.get.
    Requires url to get query
    Returns a json response.
    """
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
    """Queries OMDb for additional information about a movie given an IMDb guid.
    Requires:
        - IMDb guid to search for
        - OMDb api key
    Returns:
        - json response
    """
    omdb_querey_url = 'http://www.omdbapi.com/?i='
    omdb_querey_url = omdb_querey_url + imdb_guid + '&plot=short&apikey=' + omdb_key
    omdb_json_result = querey_omdb(omdb_querey_url)
    return omdb_json_result

def conv_milisec_to_min(miliseconds):
    """Requires int(miliseconds) and converts it to minutes.
    Returns: string(duration) (i.e. 117 min)
    """
    s, remainder = divmod(miliseconds, 1000)
    m, s = divmod(s, 60)
    min = '{} min'.format(m)
    return min

def get_video_quality(movie):
    """Takes a media object and loops through the media element to return the
    video quality formatted as a string: 1080p, 720p, 480p, SD, etc…
    Requires:
        - PlexAPI video object
    Returns: str(movie quality)
    """
    media_items = movie.media
    for elem in media_items:
        raw_quality = str(elem.videoResolution)
        quality = format_quality(raw_quality)
    if quality:
        return quality

def format_quality(raw_quality):
    """Takes video quality string and converts it to one of the following:
    1080p, 720p, 480p, SD
    """
    input_quality = str(raw_quality)
    known_qualities = ['1080', '720', '480']
    if input_quality in known_qualities:
        quality = input_quality + 'p'
    else:
        quality = input_quality.upper()
    return str(quality)

def get_filesize(movie):
    """Takes a media object and loops through the media element, then the media
    part, to return the filesize in bytes.
    Requires:
        - PlexAPI video object
    Returns:
        - str(filesize) in human readable format (i.e. 3.21 GB)
    """
    media_items = movie.media
    raw_filesize = 0
    for media_elem in media_items:
        for media_part in media_elem.parts:
            raw_filesize += media_part.size
    filesize = convert_file_size(raw_filesize)
    return filesize

def convert_file_size(size_bytes):
   """Converts file size in bytes as to human readable format.
   Requires:
        - int(bytes)
   Returns:
        - string (i.e. 3.21 GB)
   """
   if size_bytes == 0:
       return '0B'
   size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB')
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return '{} {}'.format(s, size_name[i])

def get_clean_imdb_guid(guid):
    """Takes an IMDb url and returns only the IMDb guid as a string.
    Requires:
        - str(IMDb url)
    Returns:
        - str(IMDb guid)
    """
    result = re.search('.+//(.+)\?.+', guid)
    if result:
        clean_guid = result.group(1)
        return clean_guid
    else:
        print 'ERROR - Could not determine IMDb guid from ' + guid
        sys.exit(1)

def main():
    defaults = DefaultsBundle()
    args = parse_arguments()
    debug, dryrun = slackAnnounce.get_debug_state(args, defaults)
    imdb_guid = str(args.imdb_guid)

    plex = get_server_instance(defaults)
    movie_info_plex = search_plex(plex, imdb_guid)
    new_movie = Movie(movie_info_plex, defaults)

    slack_args = SlackArgsBundle(new_movie.json_attachment,
                                 debug=debug, dryrun=dryrun)
    slack_defaults = slackAnnounce.DefaultsBundle()
    message_obj = slackAnnounce.set_slack_message(slack_args, slack_defaults)

    slackAnnounce.post_message(message_obj)

if __name__ == '__main__':
    main()