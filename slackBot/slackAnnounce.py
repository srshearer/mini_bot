#!/usr/local/bin/python -u
# encoding: utf-8

"""
About:
    Post to Slack via webhooks

To do:
    - add/improve exception handling
    - improve documentation, usage, help, etc.
    - add new movie notification functionality
"""
import os
import sys
import json
import requests
import argparse
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from slackBot import secrets


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Send messages to slack channel. Capable of sending custom '
                    'messages, maintenance up/down messages.')
    parser.add_argument('-c', '--color', dest='color', metavar='<color>',
                        required=False, action='store',
                        help='The color for message. Options: info (default), '
                             'green/good, orange/warn, red/danger, purple')
    parser.add_argument('-d', '--debug', dest='debug',
                        required=False, action='store_true',
                        help='Enable debug mode. Send message to test channel.')
    parser.add_argument('--dry', dest='dryrun',
                        required=False, action='store_true',
                        help='Enable dryrun mode. Message will not be sent.')
    parser.add_argument('--json', dest='json', metavar='<json attachment>',
                        required=False, action='store',
                        help='The message to send to the channel.')
    parser.add_argument('-m', '--message', dest='message', metavar='<message>',
                        required=True, action='store',
                        help='The message to send to the channel.')
    parser.add_argument('-r', '--room', dest='room', metavar='<room>',
                        required=False, action='store',
                        help='Slack channel room to send the message to.')
    parser.add_argument('-t', '--title', dest='title', metavar='<title>',
                        required=False, action='store',
                        help='Set a message title.')
    parser.add_argument('-u', '--user', dest='user', metavar='<username>',
                        required=False, action='store',
                        help='User to send the message as.')
    parser.add_argument('--webhook', dest='webhook_url', metavar='<url>',
                        required=False, action='store',
                        help='Override default Slack webhook url.')
    args = parser.parse_args()
    return args


class DefaultsBundle(object):
    def __init__(self):
        """The first 4 attributes may contain private information, so keep them
        in a separate file called secrets.py which is imported at the top."""
        self.webhook_url = secrets.SLACK_WEBHOOK_URL
        self.user = secrets.DEFAULT_SLACK_USER
        self.room = secrets.DEFAULT_SLACK_ROOM
        self.debugroom = secrets.DEBUG_SLACK_ROOM
        self.color = text_color('info')
        self.debug = False
        self.dryrun = False


class SlackPostJsonPayload(object):
    def __init__(self, user, room, webhook_url, json_attachments,
                 debug, dryrun):
        self.room = room
        self.user = user
        self.webhook_url = webhook_url
        self.debug = debug
        self.dryrun = dryrun
        self.json_attachments = json_attachments

        self.json_payload = {
                "channel": self.room,
                "username": self.user,
                "attachments": [
                    self.json_attachments
                ]
            }


def text_color(requested_color):
    """Takes a color alias (str) and returns the color value"""
    text_color_dict = {
        'info': '#d3d3d3',
        'good': 'good',
        'green': 'good',
        'warn': 'warning',
        'orange': 'warning',
        'danger': 'danger',
        'red': 'danger',
        'purple': '#764FA5',
    }
    if requested_color in text_color_dict:
        return_color = text_color_dict[requested_color]
    else:
        return_color = text_color_dict['default']
        print 'ERROR - Invalid color: ' + requested_color
        print 'Available colors: '.format(return_color)
        print list(text_color_dict)
        sys.exit(1)
    return return_color


def set_message_simple_message(args, defaults):
    """Sets message, title & color of message.
    Options: 'up', 'down <time amount> <time units>', or custom message.
    Requires 2 objects: args & defaults
    Returns str(message), str(title), & str(color)
    """
    arg_message = str(args.message)
    arg_message_list = arg_message.split(' ')
    if arg_message_list[0] == 'up':
        title = 'Announcement: Server is up'
        message = 'The server is back up!'
        color = text_color('good')
    elif arg_message_list[0] == 'down':
        downtime_number = arg_message_list[1]
        downtime_units = arg_message_list[2]
        title = 'Announcement: Server going down'
        message = 'The server is going down for maintenance.\nExepected ' \
                  'downtime is about {} {}.'.format(downtime_number,
                                                    downtime_units)
        color = text_color('warn')
    else:
        title = 'Server Announcement: '
        message = str(arg_message)
        if args.color:
            color = text_color(args.color)
        else:
            color = defaults.color

    if args.title:
        title = str(args.title)

    json_attachments = {
        "fallback": title,
        "color": color,
        "title": title,
        "text": message,
    }
    return json_attachments


def get_debug_state(args, defaults):
    """Determines whether or not to enable debug mode based on user options
    If dryrun mode is True, debug mode will also return True
    Requires two objects: user arguments & defaults
    Objects must contain obj.debug(bool) and obj.dryrun(bool)
    Returns debug state (bool)
    """
    if args.dryrun:
        debug_state = True
        dryrun_state = True
    else:
        debug_state = choose_arg_or_default(args, defaults, 'debug')
        dryrun_state = False
    return bool(debug_state), bool(dryrun_state)


def get_room(args, defaults):
    """Chooses Slack channel from defaults or user options (if present)
    Also ensures # is added to the front of the name if not already present
    Requires two objects: user arguments & defaults
    Objects should contain obj.room (str)
    Returns Slack channel/room (str)
    """
    try:
        arg_room = args.room
    except AttributeError:
        arg_room = False

    if arg_room:
        room = args.room
    elif args.debug:
        room = defaults.debugroom
    else:
        room = defaults.room

    hash_check = list(room)[0]
    if hash_check != '#':
        room = '#' + room
    return room


def choose_arg_or_default(args, defaults, var):
    """Chooses between user args or
    Requires:
        2 objects: user arguments & defaults
        1 variable(str)
    Objects should both potentially contain attributes with the same name
    Returns the arg value if set, otherwise returns the default value
    """
    try:
        arg_value = getattr(args, var)
    except AttributeError:
        arg_value = False
    default_value = getattr(defaults, var)
    if arg_value:
        value = arg_value
    else:
        value = default_value
    return value


def set_slack_message(args, defaults):
    """Set up necessary variables to create the SlackMessage object by
    determining whether to use a default or a user-supplied argument.
    Requires a DefaultsBundle object and an args object from argparse
    Returns a SlackMessage(object)
    """
    debug, dryrun = get_debug_state(args, defaults)
    user = str(choose_arg_or_default(args, defaults, 'user'))
    room = str(get_room(args, defaults))
    webhook_url = str(choose_arg_or_default(args, defaults, 'webhook_url'))
    try:
        json_attachments = args.json_attachments
    except AttributeError:
        json_attachments = set_message_simple_message(args, defaults)
    if debug:
        print 'User: {} \nRoom: {} \nWebhook: {} \n{}'.format(
            user, room, webhook_url, str(json.dumps(json_attachments)))

    slack_message_obj = SlackPostJsonPayload(user, room, webhook_url,
                                             json_attachments, debug, dryrun)

    if debug:
        print slack_message_obj.json_payload

    return slack_message_obj


def post_message(message_contents_obj):
    webhook_url = message_contents_obj.webhook_url
    slack_data = message_contents_obj.json_payload
    if message_contents_obj.debug:
        print '\n{}'.format(slack_data)
    if message_contents_obj.dryrun:
        print '[Dry run. Not posting message.]'
    else:
        response = requests.post(
            webhook_url, data=json.dumps(slack_data),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 200:
            raise ValueError(
                'Request to slack returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
            )
        else:
            print 'Result: ' + str(response.text)


def main():
    defaults = DefaultsBundle()
    args = parse_arguments()
    slack_message = set_slack_message(args, defaults)
    post_message(slack_message)


if __name__ == '__main__':
    main()
