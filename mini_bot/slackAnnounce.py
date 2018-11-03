#!/usr/bin/python -u
# encoding: utf-8

from __future__ import print_function, unicode_literals, absolute_import
import argparse
from mini_bot.slack_tools import slack_config
from mini_bot.slack_tools import slack_utils as su


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Send messages to slack channel. Capable of sending custom '
                    'messages, maintenance up/down messages.')
    parser.add_argument('-c', '--color', dest='color', metavar='<color>',
                        default=None, required=False, action='store',
                        help='The color for message. Options: info (default), '
                             'green/good, orange/warn, red/danger, purple')
    parser.add_argument('-d', '--debug', dest='debug', default=False,
                        required=False, action='store_true',
                        help='Enable debug mode. Send message to test channel.')
    parser.add_argument('--dry', dest='dryrun', default=False,
                        required=False, action='store_true',
                        help='Enable dryrun mode. Message will not be sent.')
    parser.add_argument('-m', '--message', dest='message', metavar='<message>',
                        default=None, required=True, action='store',
                        help='The message to send to the channel.')
    parser.add_argument('-r', '--room', dest='room', metavar='<room>',
                        default=None, required=False, action='store',
                        help='Slack channel room to send the message to.')
    parser.add_argument('-t', '--title', dest='title', metavar='<title>',
                        default=None, required=False, action='store',
                        help='Set a message title.')
    args = parser.parse_args()
    return args


def set_message(args):
    if not args.message:
        raise su.SlackException('No message given')

    if args.message.startswith('up'):
        title = 'Announcement: Server is up'
        message = 'The server is back up!'
        color = su.text_color('good')
    elif args.message.startswith('down '):
        downtime = ' '.join(args.message.split(' ')[1:])
        title = 'Announcement: Server going down'
        message = 'The server is going down for maintenance.\n' \
                  'Exepected downtime is about {}.'.format(downtime)
        color = su.text_color('warn')
    else:
        title = args.title or slack_config.DEFAULT_TITLE
        message = args.message
        color = args.color or su.text_color('info')

    json_attachments = {
        "fallback": title,
        "color": color,
        "title": title,
        "text": message,
    }

    return json_attachments


def send_slack_message(args):
    json = set_message(args)
    slack = su.SlackSender(
        json_attachments=json, room=args.room,
        debug=args.debug, dryrun=args.dryrun)
    slack.send()


def main():
    args = parse_arguments()
    send_slack_message(args)


if __name__ == '__main__':
    main()
