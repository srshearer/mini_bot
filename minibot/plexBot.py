#!/usr/bin/env python3
import argparse

from utilities import logger


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Listen for, send, and handle notifications related to "
                    "Plex content and servers")
    parser.add_argument(
        "-d", "--debug", dest="debug",
        required=False, action="store_true",
        help="Enable debug mode. Send message to test channel.")
    parser.add_argument(
        "--dry", dest="dryrun",
        required=False, action="store_true",
        help="Enable dryrun mode. Message will not be sent.")
    parser.add_argument(
        "-i", "--guid", dest="imdb_guid", metavar="<IMDb guid>",
        required=False, action="store", default=None,
        help="Find movie by IMDb guid.")
    parser.add_argument(
        "-p", "--path", dest="path", metavar="<file path>",
        required=False, action="store",
        help="Path to file.")
    parser.add_argument(
        "-s", "--sync", dest="sync_queue",
        required=False, action="store_true",
        help="Start file sync transfer queue")
    parser.add_argument(
        "--pathonly", dest="pathonly",
        required=False, action="store_true",
        help="Allow path-only sync request.")
    args = parser.parse_args()

    return args, parser


def main():
    args, parser = parse_arguments()

    if args.sync_queue:
        _codepath = "syncer"
        logger.info("Starting file syncer")
        from utilities import filesyncer

        filesyncer.run_file_syncer()

    elif args.path and args.imdb_guid:
        """Requiring imdb_guid for now until I can disambiguate movies vs 
        other media, e.g. music, tv shows, etc..."""
        _codepath = "sync request"
        logger.info(f"Sending sync request: {args.imdb_guid} - {args.path}")
        from utilities import client
        client.post_new_movie_to_syncer(
                path=args.path, imdb_guid=args.imdb_guid)

    elif args.path:
        """Best-effort attempt to parse the title and year from the filepath 
        string to retrieve the IMDb guid from OMDb."""
        _codepath = "sync request (path only)"
        if args.pathonly:
            logger.info(f"Sending path only sync request: {args.path}")
            from utilities import client
            client.post_new_movie_to_syncer(path=args.path)
        else:
            logger.info(
                f"Sync request failed. IMDb guid required: {args.path}")

    elif args.imdb_guid:
        _codepath = "notification sender"
        logger.info(f"Sending new movie notification: {args.imdb_guid}")
        from utilities import plexutils
        plexutils.send_new_movie_slack_notification(args)

    else:
        _codepath = "help"
        parser.print_help()

    logger.debug(f"Exit: {_codepath}")


if __name__ == "__main__":
    main()
