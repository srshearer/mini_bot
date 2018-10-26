#!/usr/bin/python -u
# encoding: utf-8

"""
Version: 3.0
About: Post to Slack via webhooks
"""
import os
import sys
import argparse
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '/usr/local/lib/python2.7/site-packages'))
import requests

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import slack_config


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
    args = parser.parse_args()
    return args


class DefaultsBundle(object):
    def __init__(self):
        """The first 4 attributes may contain private information, so keep them
        in a separate file called slack_config.py which is imported at the top.
        """
        self.webhook_url = slack_config.SLACK_WEBHOOK_URL
        self.webhook_url_me = slack_config.SLACK_WEBHOOK_URL_ME
        self.user = slack_config.DEFAULT_SLACK_USER
        self.room = slack_config.DEFAULT_SLACK_ROOM
        self.debugroom = slack_config.DEBUG_SLACK_ROOM
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


class SlackSender(object):
    def __init__(self, args):
        self._args = args
        self._webhook_url = slack_config.SLACK_WEBHOOK_URL
        self._webhook_url_me = slack_config.SLACK_WEBHOOK_URL_ME
        self._user = slack_config.DEFAULT_SLACK_USER
        self._room = slack_config.DEFAULT_SLACK_ROOM
        self._debugroom = slack_config.DEBUG_SLACK_ROOM
        self._color = text_color('info')
        self._debug = False
        self._dryrun = False
        self._set_debug_state()
        self._message = None
        self._room = self._set_room()
        self._user = self._set_user()
        self._json_attachments = {}
        self._json_payload = {
            "channel": self._room,
            "username": self._user,
            "attachments": [
                self._json_attachments
            ]
        }

    def _set_room(self):
        pass

    def _set_user(self):
        pass

    def _set_debug_state(self):
        """Determines whether or not to enable debug mode based on user options
        If dryrun mode is True, debug mode will also return True
        Requires two objects: user arguments & defaults
        Objects must contain obj.debug(bool) and obj.dryrun(bool)
        Returns debug state (bool)
        """
        if self._args.dryrun:
            self._debug = True
            self._dryrun = True
        elif self._args.debug:
            self._debug = True
            self._dryrun = False
        else:
            self._debug = False
            self._dryrun = False

        return

    def post_message(self):
        if self._debug:
            print '{}'.format(self._json_payload)
        if self._dryrun:
            print '[Dry run. Not posting message.]'
        else:
            response = requests.post(
                self._webhook_url, data=json.dumps(self._json_payload),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                raise ValueError(
                    'Request to slack returned an error {}, the response is: \n'
                    '{}'.format(response.status_code, response.text)
                )
            else:
                print 'Result: [{}] {}'.format(
                    response.status_code, response.text)

        return

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


def get_room_and_webhook(args, defaults):
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

    if room == 'me':
        webhook_url = str(defaults.webhook_url_me)
        room = None
    else:
        webhook_url = str(defaults.webhook_url)
        hash_check = list(room)[0]
        if hash_check != '#':
            room = '#' + room

    return webhook_url, room


def set_slack_message(args, defaults):
    """Set up necessary variables to create the SlackMessage object by
    determining whether to use a default or a user-supplied argument.
    Requires a DefaultsBundle object and an args object from argparse
    Returns a SlackMessage(object)
    """
    debug, dryrun = get_debug_state(args, defaults)
    user = defaults.user
    webhook_url, room = get_room_and_webhook(args, defaults)
    try:
        json_attachments = args.json_attachments
    except AttributeError:
        json_attachments = set_message_simple_message(args, defaults)
    if debug:
        print 'User: {} \nRoom: {}\n'.format(
            user, room)

    slack_message_obj = SlackPostJsonPayload(user, room, webhook_url,
                                             json_attachments, debug, dryrun)
    return slack_message_obj


def text_color(requested_color):
    """Takes a color alias (str) and returns the color value"""
    text_color_dict = {
        'default': '#d3d3d3',
        'info': '#d3d3d3',
        'good': 'good',
        'green': 'good',
        'warn': 'warning',
        'orange': 'warning',
        'danger': 'danger',
        'red': 'danger',
        'purple': '#764FA5'
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


def main():
    defaults = DefaultsBundle()
    args = parse_arguments()
    slack_message = set_slack_message(args, defaults)
    post_message(slack_message)


if __name__ == '__main__':
    main()
