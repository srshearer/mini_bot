#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
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
                path=args.path, imdb_guid=args.imdb_guid)

    elif args.path and not args.imdb_guid:
        logger.info('Attempting sync request')
        from utilities import server
        server.post_new_movie_to_syncer(path=args.path, imdb_guid=None)

    elif args.imdb_guid:
        logger.info('Sending new movie notification')
        from utilities import plexutils
        plexutils.send_new_movie_slack_notification(args)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
