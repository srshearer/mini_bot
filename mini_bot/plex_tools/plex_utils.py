#!/usr/bin/python -u
# encoding: utf-8

from __future__ import print_function, unicode_literals, absolute_import
import re
import sys
import math
import requests
from mini_bot.plex_tools import plex_config
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer


class PlexException(Exception):
    """Custom exception for Plex related failures."""
    pass


class OMDbException(Exception):
    """Custom exception for OMDb related failures."""
    pass


class PlexSearch(object):
    """Connects to a Plex server via PlexAPI to allow searching for media items.
    Optional kwargs:
        - auth_type (user or token): choose authentication method
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.debug = kwargs.get('debug', False)
        self.auth_type = kwargs.get('auth_type', plex_config.PLEX_AUTH_TYPE)
        self.plex_server = kwargs.get('server', plex_config.PLEX_SERVER_URL)
        self.plex = self._get_server_instance()

    def _get_server_instance(self):
        """
        Uses PlexAPI to instantiate a Plex server connection
        """
        if self.auth_type == 'user':
            plex = self._plex_account()
        elif self.auth_type == 'token':
            plex = self._plex_token()
        else:
            raise PlexException(
                'Invalid Plex connection type: {}'.format(self.auth_type))

        if self.debug:
            print('Connected: {}'.format(self.plex_server))

        return plex

    def _plex_account(self):
        """Uses PlexAPI to connect to the Plex server using an account
        and password. THis method is much slower than using a token.
        Requires:
            - IMDb guid of a movie to search for
        Returns MyPlexAccount object
        """
        if self.debug:
            print('Connecting to Plex: user auth')

        account = MyPlexAccount(
            plex_config.PLEX_USERNAME, plex_config.PLEX_PASSWORD)
        plex = account.resource(self.plex_server).connect()

        return plex

    def _plex_token(self):
        """Uses PlexAPI to connect to the Plex server using a token.
        Requires:
            - IMDb guid of a movie to search for
        Returns PlexServer object
        """
        if self.debug:
            print('Connecting to Plex: token auth')
        try:
            plex = PlexServer(plex_config.PLEX_SERVER_URL, plex_config.PLEX_TOKEN)
        except Exception as e:
            raise PlexException(
                'Failed to connect to Plex server: {} \n{}'.format(
                    self.plex_server, e)
            )

        return plex

    def movie_search(self, imdb_guid):
        """Uses PlexAPI to search for a movie via IMDb guid.
        Requires:
            - IMDb guid of a movie to search for
        Returns the first result video object.
        """
        movies = self.plex.library.section('Movies')
        found_movies = []

        if self.debug:
            print('Searching Plex: {}'.format(imdb_guid))

        for result in movies.search(guid=imdb_guid):
            found_movies.append(result)

        try:
            video = found_movies[0]
        except IndexError:
            # raise PlexException(
            # print(
            #     'Error: Could not locate movie in Plex: {} \n{}'.format(
            #         imdb_guid, self.plex_server)
            # )
            return None

        if self.debug:
            print('Found: {} ({})'.format(video.title, video.year))

        return video

    def recently_added(self):
        movies = self.plex.library.recentlyAdded()
        return movies


class OmdbSearch(object):
    """Queries OMDb.org for movie information using an IMDb guid."""
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False)
        self._omdb_key = plex_config.OMDB_API_KEY

    def _get_omdb_url(self, imdb_guid):
        omdb_url = 'http://www.omdbapi.com/?i={}&plot=short&apikey={}'.format(
            imdb_guid, self._omdb_key
        )

        return omdb_url

    def search(self, imdb_guid):
        """Generic function to query a url via requests.get.
        Requires url to get query
        Returns a json response.
        """
        if self.debug:
            print('Searching OMDb: {}'.format(imdb_guid))

        omdb_query_url = self._get_omdb_url(imdb_guid)
        if self.debug:
            print('Query url: {}'.format(omdb_query_url))

        response = requests.get(
            omdb_query_url,
            headers={'Content-Type': 'application/json'}
        )

        if self.debug:
            print('Response: {} \n{}'.format(
                response.status_code, response.text))

        if response.status_code != 200:
            raise ValueError(
                'Request to slack returned an error {}, the response is:\n'
                '{}'.format(response.status_code, response.text)
            )
        else:
            return response.text


def conv_millisec_to_min(milliseconds):
    """Requires int(milliseconds) and converts it to minutes.
    Returns: string(duration) (i.e. 117 min)
    """
    s, remainder = divmod(milliseconds, 1000)
    m, s = divmod(s, 60)
    minute_string = '{} min'.format(m)
    return minute_string


def get_video_quality(movie):
    """Takes a media object and loops through the media element to return the
    video quality formatted as a string: 1080p, 720p, 480p, SD, etc…
    Requires:
        - PlexAPI video object
    Returns: str(movie quality)
    """
    media_items = movie.media
    quality = 'SD'
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
        print('ERROR - Could not determine IMDb guid: {}'.format(guid))
        sys.exit(1)
