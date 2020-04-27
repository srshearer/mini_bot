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
        logger.info(f"Response: [{r.status_code}] {r.text}")

    except requests.exceptions.ConnectionError:
        logger.error("Response: [404] Server not found")

    except requests.exceptions.ReadTimeout:
        logger.error(
            f"[503] Request timed out. No response after {timeout} seconds")
