#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import os.path
import argparse
from utilities import logger


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Listen for, send, and handle notifications related to '
                    'Plex content and servers')
    parser.add_argument('-d', '--debug', dest='debug',
                        required=False, action='store_true',
                        help='Enable debug mode. Send message to test channel.')
    parser.add_argument('--dry', dest='dryrun',
                        required=False, action='store_true',
                        help='Enable dryrun mode. Message will not be sent.')
    parser.add_argument('-i', '--guid', dest='imdb_guid', metavar='<IMDb guid>',
                        required=False, action='store',
                        help='Find movie by IMDb guid.')
    parser.add_argument('-p', '--path', dest='path', metavar='<file path>',
                        required=False, action='store', help='Path to file.')
    parser.add_argument('-s', '--server', dest='sync_server',
                        required=False, action='store_true',
                        help='Run flask server listening at endpoint for new '
                             'movies to sync.')
    parser.add_argument('-t', '--transfer', dest='transfer',
                        required=False, action='store_true',
                        help='Loop the file transfer queue.')
    args = parser.parse_args()

    return args, parser


def main():
    args, parser = parse_arguments()

    if args.sync_server:
        logger.info('Starting server')
        from utilities import server

        server.run_server(debug=args.debug)

    elif args.path and args.imdb_guid:
        logger.info('Sending sync request')
        from utilities import server

        server.post_new_movie_to_syncer(
                imdb_guid=args.imdb_guid, path=args.path)

    elif args.imdb_guid:
        logger.info('Sending new movie notification')
        from utilities import plexutils
        plexutils.send_new_movie_slack_notification(args)

    elif args.transfer:
        logger.info('Starting queue...')
        from utilities import db_utils, filesyncer

        _database = 'remote_movies.db'
        _db_path = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), _database))
        _schema = 'schema.sql'
        _schema_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), _schema))

        filesyncer.transfer_queue_loop(
            db_utils.FileTransferDB(db_path=_db_path, schema_path=_schema_path))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
