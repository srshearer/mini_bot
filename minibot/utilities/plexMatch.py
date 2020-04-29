#!/usr/bin/env python3
import os.path
import pickle
import time
import sys
from requests.exceptions import ConnectTimeout
from utilities import config
from utilities import server
from utilities import plexutils
from plexapi.server import PlexServer

movies_file_cbs = os.path.abspath("movies_cbs.pickle")
movies_file_srs = os.path.abspath("movies_srs.pickle")
processed_movies_file = os.path.abspath("processed_movies.pickle")


def save_pickle(data, pickle_file):
    with open(pickle_file, "wb") as f:
        pickle.dump(data, f)


def load_pickle(pickle_file):
    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as f:
            return pickle.load(f)
    print(f"FAILED TO LOAD PICKLE: {pickle_file}")
    return


def get_plex_data(server):
    print("connecting to {} ...".format(server))
    try:
        plex = PlexServer(server, config.PLEX_TOKEN)
    except ConnectTimeout as e:
        print(f" * ERROR: ConnectionTImeout\n{str(e)}")
        sys.exit(1)

    print(f"connected: {plex.friendlyName} - {plex.machineIdentifier}")

    all_movies = []
    for m in plex.library.section("Movies").all():
        title = m.title
        year = m.year
        guid = plexutils.get_clean_imdb_guid(m.guid)
        files = m.locations
        m_info = (guid, title, year, files)
        all_movies.append(m_info)

    print(f"{server} total: {len(all_movies)}")

    if len(all_movies) > 0:
        return all_movies
    else:
        return None


def compare_saved_plex_data(movies_original, movies_new):
    guids_original = []
    for m in movies_original:
        if m[0]:
            guids_original.append(m[0])

    unique_movies = []
    for m in movies_new:
        if m[0] and m[0] not in guids_original and m[0] not in config.blacklist:
            unique_movies.append(m)

    return unique_movies


def sync(unique):
    try:
        print(f"unique: {len(unique)}")
        for u in unique:
            guid = u[0]
            titleyear = str(f"{u[1]} ({u[2]})")
            filepath = str(u[3][0])
            print(f"{titleyear} - {u}")

            if titleyear and guid and filepath:
                print(f"\tSending sync request: {titleyear} [{guid}]"
                      f" - [{filepath}]")
                server.post_new_movie_to_syncer(path=filepath, imdb_guid=guid)
                time.sleep(2)
            else:
                print(f" * ERROR: missing data: {u}")

    except Exception as e:
        raise e


def main():
    # get movie data from servers and cache locally
    cbs_movies = get_plex_data(config.PLEX_SERVER_URL_CBS)
    if cbs_movies:
        save_pickle(cbs_movies, movies_file_cbs)

    srs_movies = get_plex_data(config.PLEX_SERVER_URL)
    if srs_movies:
        save_pickle(srs_movies, movies_file_srs)

    # load cached data and sync unique items
    movies_srs = load_pickle(movies_file_srs)
    movies_cbs = load_pickle(movies_file_cbs)
    unique = compare_saved_plex_data(movies_srs, movies_cbs)
    sync(unique)


if __name__ == "__main__":
    main()
