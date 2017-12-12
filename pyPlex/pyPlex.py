#!/usr/bin/python -u
# encoding: utf-8

"""
Steven Shearer / srshearer@gmail.com

About:
    For interacting with a Plex server to extract information out to build a
    json message.

To do:
    - add/improve exception handling
    - improve documentation, usage, help, etc
    - extract link to movie poster image
    - get token based auth working
    - build new movie class
    - figure out how to export the movie instance as a json attachment object to
      an outside script
"""

import os
import re
import sys
import json
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '/usr/local/lib/python2.7/site-packages'))
import requests
# from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pyPlex import secrets
from pyBots.slackBot import slackAnnounce


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
        self.plex_server_url = secrets.PLEX_SERVER_URL
        self.plex_server_name = secrets.PLEX_SERVER_NAME
        self.user = secrets.PLEX_USERNAME
        self.pw = secrets.PLEX_PASSWORD
        self.token = secrets.PLEX_TOKEN
        self.omdb_key = secrets.OMDB_API_KEY
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
        self.color = defaults.color
        self.title = str(movie_info_plex.title)
        self.year = str(movie_info_plex.year)
        self.imdb_guid = imdb_guid
        self.director = movie_info_omdb.director
        self.rating = str(movie_info_plex.contentRating)
        self._raw_duration = movie_info_plex.duration
        self.duration = conv_milisec_to_min(self._raw_duration)
        self.add_date = str(movie_info_plex.addedAt)
        self.plot = movie_info_omdb.plot
        self.media_items = movie_info_plex.media
        self.poster_link = movie_info_omdb.poster_link
        self.quality = get_duration(movie_info_plex)

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
        self.revenue = self.data['BoxOffice']
        self.duration = self.data['Runtime']


def choose_arg_or_default(args, defaults, var):
    """Chooses user args if passed in, or defaults if not
    Requires:
        two objects: user arguments & defaults
        one variable(str) as an attribute to look for in the objects
    Objects should both potentially contain attributes with the same name
    """
    try:
        arg_value = getattr(args, var)
    except AttributeError:
        arg_value = False
    default_value = getattr(defaults, var)
    if arg_value:
        value = arg_value
    else:
        value = default_value
    return value

def get_clean_imdb_guid(guid):
    result = re.search('.+//(.+)\?.+', guid)
    if result:
        clean_guid = result.group(1)
        return clean_guid
    else:
        print 'ERROR - Could not determine IMDb guid from ' + guid
        sys.exit(1)

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
    for video in movies.search(guid=imdb_guid):
        print(video.title)
    return video

def get_new_movie_notification_json(movie):
    pretext = 'New Movie Available: '
    movie_title_year = '{} ({})'.format(movie.title, movie.year)
    fallback = '{} {}'.format(pretext, movie_title_year)
    color = movie.color
    imdb_guid = movie.imdb_guid
    duration = movie.duration
    plot = movie.plot
    director = movie.director
    rating = movie.rating
    poster_link = movie.poster_link

    json_attachments = {
        "fallback": fallback,
        "color": color,
        "pretext": pretext,
        "title": movie_title_year,
        "title_link": 'http://www.imdb.com/title/' + imdb_guid,
        "text": duration,
        "footer": '{} \n\nDirected by: {} \nRuntime: {} \n'
                  'Rated [{}]'.format(plot, director, duration, rating),
        "image_url": poster_link,
    }
    return json_attachments


def main():
    defaults = DefaultsBundle()
    args = parse_arguments()

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

    # raw_imdb_guid = args.imdb_guid
    # imdb_guid = get_clean_imdb_guid(raw_imdb_guid)

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

    slack_variables = SlackArgsBundle(json_attachments, debug=True, dryrun=False)
    slack_defaults = slackAnnounce.DefaultsBundle()
    message_obj = slackAnnounce.set_slack_message(slack_variables, slack_defaults)
    slackAnnounce.post_message(message_obj)


    # movie_section = plex.library.section('Movies')
    # recently_added_movies_list = movie_section.recentlyAdded(maxresults=maxresults)
    #
    # print_info_for_results(recently_added_movies_list)

"""
- Steps -

- called explicitly (via plexpy)
- some info about the new movie is passed in as an arg (imdb guid)
✔ search for movie in plex recently added
- gather movie info 
✔︎ build json
✔︎ send message to slack via slackAnnounce
"""

if __name__ == '__main__':
    main()

    # guid = 'com.plexapp.agents.imdb://tt3606752?lang=en'

    # {"Title": "Cars 3",
    #  "Year": "2017",
    #  "Rated": "G",
    #  "Released": "16 Jun 2017",
    #  "Runtime": "102 min",
    #  "Genre": "Animation, Adventure, Comedy",
    #  "Director": "Brian Fee",
    #  "Writer": "Brian Fee (original story by), Ben Queen (original story by), Eyal Podell (original story by), Jonathon E. Stewart (original story by), Kiel Murray (screenplay by), Bob Peterson (screenplay by), Mike Rich (screenplay by), Scott Morse (additional story material)",
    #  "Actors": "Owen Wilson, Cristela Alonzo, Chris Cooper, Nathan Fillion",
    #  "Plot": "Lightning McQueen sets out to prove to a new generation of racers that he's still the best race car in the world.",
    #  "Language": "English", "Country": "USA", "Awards": "2 nominations.",
    #  "Poster": "https://images-na.ssl-images-amazon.com/images/M/MV5BMTc0NzU2OTYyN15BMl5BanBnXkFtZTgwMTkwOTg2MTI@._V1_SX300.jpg",
    #  "Ratings": [{"Source": "Internet Movie Database", "Value": "6.9/10"},
    #              {"Source": "Rotten Tomatoes", "Value": "67%"},
    #              {"Source": "Metacritic", "Value": "59/100"}],
    #  "Metascore": "59", "imdbRating": "6.9", "imdbVotes": "29,868",
    #  "imdbID": "tt3606752",
    #  "Type": "movie",
    #  "DVD": "07 Nov 2017",
    #  "BoxOffice": "$152,603,003",
    #  "Production": "Walt Disney Pictures",
    #  "Website": "http://movies.disney.com/cars-3",
    #  "Response": "True"}

    # class Movie(object):
    #     def __init__(self, movie):
    #         self.title = movie.title
    #         self.year = '1985'
    #         self.color = slackAnnounce.text_color('purple')
    #         self.imdb_guid = movie.imdb_guid
    #         self.duration = '120 min'
    #         self.plot = 'plot'
    #         self.director = 'director'
    #         self.rating = 'R'
    #         self.poster_link = 'https://images-na.ssl-images-amazon.com/images/M/MV5BMTc0NzU2OTYyN15BMl5BanBnXkFtZTgwMTkwOTg2MTI@._V1_SX300.jpg'
    #
    #     def json_attachment(self):
    #         json_attachment = new_movie_notification(self)
    #         return json_attachment

# def print_info_for_results(movie_list):
#     for result in movie_list:
#         try:
#             title = str(result.title)
#             year = str(result.year)
#             rating = str(result.contentRating)
#             raw_duration = result.duration
#             duration = conv_milisec_to_min(raw_duration)
#             # add_date = str(result.addedAt)
#             # summary = str(result.summary)
#             media_items = result.media
#             raw_imdb_guid = result.guid
#             imdb_guid = get_clean_imdb_guid(raw_imdb_guid)
#             poster = get_poster(imdb_guid)
#             for elem in media_items:
#                 raw_quality = str(elem.videoResolution)
#                 quality = format_quality(raw_quality)
#
#             print '{} ({}) {} [{}, {}] {} - {}'.format(title, year, imdb, rating, quality, duration, poster)
#
#         except:
#             pass