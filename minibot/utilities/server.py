#!/usr/bin/env python3
import json
import os.path
import sqlite3

from flask import Flask, request

from utilities import config
from utilities import db
from utilities import logger
from utilities import omdb
from utilities import plexutils

app = Flask(__name__)


@app.route("/", methods=['GET'])
def hello_world():
    return 200, "Hello, World!"


@app.route(config.TEST_ENDPOINT, methods=['GET'])
def test():
    return 200, "Test successful"


def handle_movie_sync_request(raw_request, debug=False):
    request_data = {
        "title": None,
        "year": None,
        "guid": None,
        "path": None,
        "status": None,
    }

    if not raw_request['path']:
        request_data['status'] = f"No remote path for file: {raw_request}"
        return 400, request_data
    else:
        request_data['path'] = raw_request['path']

    _omdb = omdb.OMDb(api_key=config.OMDB_API_KEY, debug=debug)

    if raw_request['guid']:
        imdb_guid = raw_request['guid']
        omdb_status, result = _omdb.search(imdb_guid=imdb_guid)
    else:
        clean_path = os.path.basename(request_data['path'])

        t, y = plexutils.get_title_year_from_path(clean_path)
        request_data['title'] = t
        request_data['year'] = y
        omdb_status, result = _omdb.search(
            title=request_data['title'], year=request_data['year'])

    if not omdb_status == 200:
        request_data['status'] = f"Error locating movie in OMDB: {raw_request}"
        return omdb_status, request_data

    try:
        if not result['Type']:
            request_data['status'] = f"Unable to determine content type: " \
                                     f"{raw_request}"
            return 415, request_data

        if not result['Type'] == "movie":
            request_data['status'] = f"Content type is not movie: " \
                                     f"{result['Type']} | {raw_request}"
            return 415, request_data

    except TypeError:
        request_data['status'] = f"Unable to determine content type: " \
                                 f"{raw_request}"
        return 415, request_data

    try:
        request_data['guid'] = result['imdbID']
        request_data['title'] = result['Title']
        request_data['year'] = result['Year']

    except KeyError as e:
        request_data['status'] = f"Movie not found: {raw_request} | {str(e)}"
        return 404, request_data

    except Exception as e:
        request_data['status'] = f"Unknown exception: {raw_request} | {str(e)}"
        return 400, request_data

    if not request_data['title']:
        request_data['status'] = f"Missing title: {raw_request}"
        return 404, request_data

    if not request_data['guid']:
        request_data['status'] = f"Missing guid: {raw_request}"
        return 404, request_data

    if not request_data['path']:
        request_data['status'] = f"Missing path: {raw_request}"
        return 400, request_data

    request_data['status'] = "Success"
    return 200, request_data


@app.route(config.NEW_MOVIE_ENDPOINT, methods=['POST'])
def sync_new_movie():
    debug = False
    raw_request = request.get_json()
    logger.info(f"Request: {raw_request}", stdout=True)

    r_code, r = handle_movie_sync_request(raw_request, debug=debug)
    logger.debug(f"Result: {r_code} - {r}")

    if r_code == 200:
        try:
            if debug:
                logger.debug(f"Inserting into db: "
                             f"{r['guid']} / {r['path']} \n{r}")
            db.insert(guid=r['guid'], remote_path=r['path'])
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in e.message:
                logger.warning(f"Skipping request. Already in database: "
                               f"{r['guid']}")
                r_code = 208
                r['status'] = "Item already requested"
        except Exception as e:
            logger.error(f"Exception in db insert time: \n{str(e)}\n\n")
            raise

    else:
        logger.warning(f"{r_code} - {r['status']}")

    return r['status'], r_code
