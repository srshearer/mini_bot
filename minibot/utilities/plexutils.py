#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import re
import json
import requests
from utilities import logger
from utilities import config
from utilities import utils
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from slackannounce.utils import SlackSender, text_color


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
    def __init__(self, debug=False, auth_type=config.PLEX_AUTH_TYPE,
                 server=config.PLEX_SERVER_URL, **kwargs):
        self.kwargs = kwargs
        self.debug = debug
        self.auth_type = auth_type
        self.plex_server = server
        self.plex = None

    def connect(self, auth_type=None):
        """
        Uses PlexAPI to instantiate a Plex server connection
        """
        if not auth_type:
            auth_type = self.auth_type

        logger.debug('Connecting to Plex: {}'.format(auth_type))

        if auth_type == 'user':
            plex = self._plex_account()
        elif auth_type == 'token':
            plex = self._plex_token()
        else:
            raise PlexException(
                'Invalid Plex connection type: {}'.format(self.auth_type))

        self.plex = plex
        logger.debug('Connected: {}'.format(self.plex_server))

        return plex

    def _plex_account(self):
        """Uses PlexAPI to connect to the Plex server using an account
        and password. THis method is much slower than using a token.
        Requires:
            - IMDb guid of a movie to search for
        Returns MyPlexAccount object
        """
        if not config.PLEX_USERNAME or not config.PLEX_PASSWORD:
            raise PlexException('Plex username or password missing from '
                                'config.py: {}'.format(self.auth_type))

        try:
            account = MyPlexAccount(
                config.PLEX_USERNAME, config.PLEX_PASSWORD)
            plex = account.resource(config.PLEX_SERVER_NAME).connect()
        except Exception as e:
            raise PlexException(
                'Failed to connect to Plex server: {} \n{}'.format(
                    self.plex_server, e))

        return plex

    def _plex_token(self):
        """Uses PlexAPI to connect to the Plex server using a token.
        Requires:
            - IMDb guid of a movie to search for
        Returns PlexServer object
        """
        if not config.PLEX_SERVER_URL or not config.PLEX_TOKEN:
            raise PlexException(
                'Plex token or url config.py: {}'.format(self.auth_type))

        try:
            plex = PlexServer(config.PLEX_SERVER_URL, config.PLEX_TOKEN)
        except Exception as e:
            raise PlexException(
                'Failed to connect to Plex server: {} \n{}'.format(
                    self.plex_server, e))

        return plex

    def movie_search(self, guid=None, title=None, year=None):
        """Uses PlexAPI to search for a movie via IMDb guid, title, and/or year.
        Requires one or more:
            - Movie guid from IMDb (str)
            - Movie title (str)
            - Movie year (str): Only used if title is given
        Returns: A list of PlexAPI video objects (list)
        """
        if not self.plex:
            self.connect()

        found_movies = []
        if not guid and not title:
            logger.error(
                'Error: plexutils.movie_search() requires guid or title.')
            return found_movies

        movies = self.plex.library.section('Movies')

        if self.debug:
            logger.debug('Searching Plex: {}'.format(guid))

        if guid:
            for m in movies.search(guid=guid):
                found_movies.append(m)
        if title:
            for m in movies.search(title=title, year=year):
                if m not in found_movies:
                    found_movies.append(m)

        return found_movies

    def recently_added(self):
        if not self.plex:
            self.connect()

        return self.plex.library.recentlyAdded()

    def in_plex_library(self, guid=None, title=None, year=None):
        if not self.plex:
            self.connect()

        results = self.movie_search(
            guid=guid, title=title, year=year)

        if results:
            in_plex = True
        else:
            in_plex = False

        return in_plex


class MovieNotification(object):
    """Creates an object for searching a Plex server and OMDb for relevant info
    about a given movie and formatting a json notification for Slack.
    """
    def __init__(self, debug=False, **kwargs):
        self.debug = debug
        self.imdb_guid = None
        self.color = text_color('purple')
        self._plex_helper = PlexSearch(**kwargs)
        self._plex_result = None
        self._omdb_result = None

    def search(self, imdb_guid):
        """Searches Plex via PlexAPI and OMDb for a movie using an IMDb guid.
        Requires:
            - str(imdb_guid)
        Returns:
            - json(rich slack notification)
        """
        self.imdb_guid = imdb_guid

        _, self._omdb_result = omdb_guid_search(imdb_guid, debug=self.debug)

        plex_results = self._plex_helper.movie_search(imdb_guid)
        if plex_results:
            self._plex_result = plex_results[0]
        else:
            self._plex_result = None

        return self._json_attachment

    @property
    def _json_attachment(self):
        """Formatted json attachment suitable for sending a rich
        Slack notification.
        """
        quality = get_video_quality(self._plex_result)
        filesize = get_filesize(self._plex_result)

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


def omdb_guid_search(imdb_guid, debug=False):
    """Querie OMDb.org for movie information using a provided IMDb guid and
    return the response.
    Requires: imdb_guid(str)
    Returns url(str)
    """

    query = '?i={}&plot=short'.format(imdb_guid)

    if debug:
        logger.debug('Searching OMDb: {}'.format(imdb_guid))

    status, response_json = _query_omdb(query)

    return status, response_json


def omdb_title_search(title, year=None, debug=False):
    """Queries OMDb.org for movie information using a title and
    optionally, a year.
    Requires: title(str) - movie title
              year(str)  - year movie was made (optional)
    Returns url(str)
    """
    query = '?t={}'.format(title)
    if year:
        query = query + '&y={}'.format(year)
    query = query + '&plot=short'

    if debug:
        logger.debug('Searching OMDb: {} {}'.format(title, year))

    status, response_json = _query_omdb(query)

    return status, response_json


def _query_omdb(query, debug=False):
    omdb_query_url = 'http://www.omdbapi.com/{}&apikey={}'.format(
        query, config.OMDB_API_KEY)

    if debug:
        logger.debug('Query url: {}'.format(omdb_query_url))

    response = requests.get(
        omdb_query_url,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code != 200:
        logger.error('OMDb responded with an error')
        logger.debug('Response: [{}] - {}'.format(
            response.status_code, response.text))

    elif debug:
        logger.debug('Response: [{}] - {}'.format(
            response.status_code, response.text))

    return response.status_code, json.loads(response.text)


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

    if args.debug:
        logger.debug(movie_json)

    logger.info('Sending to slack_announce')
    slack = SlackSender(
        json_attachments=movie_json,
        debug=args.debug,
        dryrun=args.dryrun
    )

    slack.send()


def get_video_quality(video):
    """Takes a media object and loops through the media element to return the
    video quality formatted as a string.
    Requires:
        - PlexAPI video object
    Returns: movie quality (str) - i.e. 1080p, 720p, 480p, SD
    """
    media_items = video.media
    quality = 'SD'

    for elem in media_items:
        raw_quality = str(elem.videoResolution)
        quality = format_quality(raw_quality)

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
    filesize = utils.convert_file_size(raw_filesize)

    return filesize


def get_clean_imdb_guid(guid):
    """Takes an IMDb url and returns only the IMDb guid as a string.
    Requires:
        - str(IMDb url)
    Returns:
        - str(IMDb guid)
    """
    url_pattern = '[.+\.]?imdb.com/title/([A-Za-z]{2}[\d]{5,8})(/?.+?|$)'
    plex_pattern = '.+://([A-Za-z]{2}[\d]{5,8})\?.+'

    result = re.search(url_pattern, guid)
    if not result:
        result = re.search(plex_pattern, guid)

    if result:
        clean_guid = result.group(1)
    else:
        clean_guid = None

    return clean_guid
