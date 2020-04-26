#!/usr/bin/python3 -u
import json
import os.path
import sqlite3

import requests
from flask import Flask, request

from utilities import config
from utilities import dbutils
from utilities import logger
from utilities import omdb
from utilities import plexutils
from utilities.filesyncer import TransferQueue
from utilities.utils import SigInt
from utilities.utils import retry

_NEW_MOVIE_ENDPOINT = "/new_movie/"


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
        t, y = plexutils.get_title_year_from_path(
            clean_path)
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


def post_new_movie_to_syncer(path, imdb_guid=None, timeout=60):
    movie_info_dict = {
        "path": path,
        "guid": imdb_guid,
    }

    movie_data = json.dumps(movie_info_dict)

    url = config.REMOTE_LISTENER + _NEW_MOVIE_ENDPOINT
    logger.debug(f"Posting request to: {url} - {movie_data}")

    try:
        r = requests.post(
            url, movie_data,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        logger.info(f"Response: [{r.status_code}] {r.text}")

    except requests.exceptions.ConnectionError:
        logger.error("Response: [404] Server not found")

    except requests.exceptions.ReadTimeout:
        logger.error(
            f"[503] Request timed out. No response after {timeout} seconds")


@retry(delay=3, logger=logger)
def run_server(run_queue=True, debug=False):
    app = Flask(__name__)
    _db = dbutils.FileTransferDB()
    logger.debug(f"db exists?: {os.path.exists(_db.db_path)} | {_db.db_path}")
    q = TransferQueue(_db)

    @app.route(_NEW_MOVIE_ENDPOINT, methods=['POST'])
    def sync_new_movie():
        raw_request = request.get_json()
        logger.info(f"Request: {raw_request}", stdout=True)

        r_code, r = handle_movie_sync_request(raw_request, debug=debug)
        logger.debug(f"Result: {r_code} - {r}")

        if r_code == 200:
            try:
                if debug:
                    logger.debug(
                        f"Inserting into db: {r['guid']} / {r['path']} \n{r}")
                _db.insert(guid=r['guid'], remote_path=r['path'])
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in e.message:
                    logger.warning(
                        f"Skipping request. Already in database: {r['guid']}")
                    r_code = 208
                    r['status'] = "Item already requested"
            except Exception as e:
                logger.error(f"Exception in db insert time: \n{e}\n\n")
                raise

        else:
            logger.warning(f"{r_code} - {r['status']}")

        return r['status'], r_code

    try:
        if run_queue:
            logger.debug("starting queue")
            q.start()

        logger.debug("starting listener")
        if debug:
            app.run(port=5000, debug=True)
        else:
            app.run(host="0.0.0.0", port=5000)

    except SigInt as e:
        logger.debug(e)
        logger.info("Exiting...")

    except Exception as e:
        logger.error(f"Unknown exception: \n{e}")

    finally:
        logger.info("Stopping server and transfer queue")
        q.stop()
        logger.info("Server and transfer queue stopped")
