#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import sys
import os.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
from minibot import logger


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
    parser.add_argument('-t', '--transfer', dest='transfer',
                        required=False, action='store_true',
                        help='Loop the file transfer queue.')
    parser.add_argument('-i', '--guid', dest='imdb_guid', metavar='<IMDb guid>',
                        required=False, action='store',
                        help='Find movie by IMDb guid.')
    parser.add_argument('-l', '--listen', dest='sync_listen',
                        required=False, action='store_true',
                        help='Run flask server listening at endpoint for new '
                             'movies to sync.')
    parser.add_argument('-p', '--path', dest='path', metavar='<file path>',
                        required=False, action='store', help='Path to file.')
    args = parser.parse_args()

    return args, parser


def main():
    args, parser = parse_arguments()

    if args.sync_listen:
        logger.info('Starting listener')
        from minibot.utilities import server
        server.run_server(debug=args.debug)
    elif args.path and args.imdb_guid:
        logger.info('Sending sync request')
        from minibot.utilities import server
        server.post_new_movie_to_syncer(
                imdb_guid=args.imdb_guid, path=args.path)
    elif args.imdb_guid:
        logger.info('Sending new movie notification')
        from minibot.utilities import plexutils
        plexutils.send_new_movie_slack_notification(args)
    elif args.transfer:
        logger.info('Starting queue...')
        from minibot.utilities import db_utils, filesyncer
        filesyncer.transfer_queue_loop(db_utils.FileTransferDB())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
