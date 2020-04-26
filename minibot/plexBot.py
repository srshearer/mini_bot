#!/usr/bin/python3 -u
# encoding: utf-8
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
                        required=False, action='store', default=None,
                        help='Find movie by IMDb guid.')
    parser.add_argument('-p', '--path', dest='path', metavar='<file path>',
                        required=False, action='store', help='Path to file.')
    parser.add_argument('-s', '--server', dest='sync_server',
                        required=False, action='store_true',
                        help='Run flask server listening at endpoint for new '
                             'movies to sync.')
    parser.add_argument('--notransfer', dest='no_transfer',
                        required=False, action='store_true',
                        help='Run server without starting transfer queue.')
    parser.add_argument('--pathonly', dest='pathonly',
                        required=False, action='store_true',
                        help='Allow path-only sync request.')
    args = parser.parse_args()

    return args, parser


def main():
    args, parser = parse_arguments()

    if args.sync_server:
        _codepath = 'server'
        logger.info('Starting server')
        from utilities import server
        run_queue = True
        if args.no_transfer:
            run_queue = False

        server.run_server(run_queue=run_queue, debug=args.debug)

    elif args.path and args.imdb_guid:
        '''Send a request with a local filepath and the imdb guid of a movie to 
        a remote media server to pull a file'''
        _codepath = 'sync request'
        logger.info('Sending sync request: {} - {}'.format(
            args.imdb_guid, args.path
        ))
        from utilities import server
        server.post_new_movie_to_syncer(
                path=args.path, imdb_guid=args.imdb_guid)

    elif args.path:
        '''Best-effort attempt to parse the title and year from the filepath string to 
        retrieve the IMDb guid from OMDb.'''
        _codepath = 'sync request (path only)'
        if args.pathonly:
            logger.info('Sending path only sync request: {}'.format(args.path))
            from utilities import server
            server.post_new_movie_to_syncer(path=args.path)
        else:
            logger.info(
                'Sync request failed. IMDb guid required: {}'.format(args.path))

    elif args.imdb_guid:
        _codepath = 'notification sender'
        logger.info('Sending new movie notification: {}'.format(args.imdb_guid))
        from utilities import plexutils
        plexutils.send_new_movie_slack_notification(args)

    else:
        _codepath = 'help'
        parser.print_help()

    logger.debug('Exit: {}'.format(_codepath))


if __name__ == '__main__':
    main()
