#!/usr/bin/env python3
import json
import requests
from utilities import config
from utilities import logger


def post_new_movie_to_syncer(path, imdb_guid=None, timeout=60):
    movie_info_dict = {
        "path": path,
        "guid": imdb_guid,
    }

    movie_data = json.dumps(movie_info_dict)

    url = config.REMOTE_LISTENER + config.NEW_MOVIE_ENDPOINT
    logger.debug(f"Posting request to: {url} - {movie_data}")

    try:
        r = requests.post(
            url, movie_data,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        logger.info(f"Response: {r.text} [{r.status_code}]")

    except requests.exceptions.ConnectionError:
        logger.error("Response: Server not found [404]")

    except requests.exceptions.ReadTimeout:
        logger.error(
            f" Request timed out. No response after {timeout} seconds [503]")


def get_test_endpoint(timeout=10):
    url = config.REMOTE_LISTENER + config.TEST_ENDPOINT
    logger.debug(f"Sending get request to: {url}")

    try:
        r = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        logger.info(f"Response: {r.text} [{r.status_code}]")

    except requests.exceptions.ConnectionError:
        logger.error("Response: [404] Server not found")

    except requests.exceptions.ReadTimeout:
        logger.error(
            f"Request timed out. No response after {timeout} seconds [503] ")
