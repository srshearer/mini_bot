#!/usr/bin/python -u
# encoding: utf-8

from __future__ import print_function, unicode_literals, absolute_import
import json
import requests
from mini_bot.slack_tools import slack_config


class SlackException(Exception):
    """Custom exception for Slack related failures."""
    pass


class SlackSender(object):
    def __init__(self, json_attachments=None, **kwargs):
        self.debug = kwargs.get('debug', False)
        self.dryrun = kwargs.get('dryrun', False)
        self.room = kwargs.get('room', None)
        self.color = kwargs.get('color', text_color('info'))
        self._set_debug_state()
        self._room = self._set_room()
        self._webhook_url = self._set_webhook()
        self._user = slack_config.DEFAULT_SLACK_USER
        self.json_attachments = json_attachments
        self._json_attachments = self._set_json_attachments()
        self._json_payload = {}

    def _set_debug_state(self):
        """Determines whether or not to enable debug mode based on user options
        If dryrun mode is True, debug mode will also return True
        Requires two objects: user arguments & defaults
        Objects must contain obj.debug(bool) and obj.dryrun(bool)
        Returns debug state (bool)
        """
        if self.dryrun:
            self.debug = True
            self.dryrun = True
        elif self.debug:
            self.debug = True
            self.dryrun = False
        else:
            self.debug = False
            self.dryrun = False

        return

    def _set_room(self):
        if self.debug:
            room = slack_config.DEBUG_SLACK_ROOM
        elif self.room:
            room = self.room
        else:
            room = slack_config.DEFAULT_SLACK_ROOM

        return room

    def _set_json_attachments(self):
        if self.json_attachments:
            _json_attachments = self.json_attachments
        else:
            _json_attachments = {}

        return _json_attachments

    def _set_webhook(self):
        if self.room == 'me':
            webhook_url = slack_config.SLACK_WEBHOOK_URL_ME
            self._room = None
        else:
            webhook_url = slack_config.SLACK_WEBHOOK_URL
            hash_check = list(self._room)[0]

            if hash_check != '#':
                self._room = '#' + self._room

        return webhook_url

    def set_simple_message(self, message='', **kwargs):
        """Sets formatted json to use in sending a Slack notification using only
        a provided message.
        Requires:
            - str(message): The body text of the message
        Optional:
            - str(title): The title of the message
            - str(color): The color of the message
            - str(fallback): The fallback text. Same as title by default
        Returns:
            - json(self.json_attachments): The formatted json set in the object
        """
        title = kwargs.get('title', slack_config.DEFAULT_TITLE)
        color = kwargs.get('color', self.color)
        fallback = kwargs.get('fallback', None)

        self.json_attachments = {
            "fallback": fallback or title,
            "color": color,
            "title": title,
            "text": message,
        }
        return self.json_attachments

    def send(self):
        """Send the Slack notification with the current json_attachments.
        This will update the debug state, room, and webhook before sending.
        """
        self._set_debug_state()
        self._set_room()
        self._set_webhook()
        self._json_payload = {
            "channel": self._room,
            "username": self._user,
            "attachments": [
                self.json_attachments
            ]
        }

        if self.debug:
            print('{}'.format(self._json_payload))
        if self.dryrun:
            print('[Dry run. Not posting message.]')
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
                print('Result: [{}] {}'.format(
                    response.status_code, response.text))

        return


def text_color(requested_color):
    """Takes a color alias (str) and returns the color value if available"""
    colors = {
        'grey': '#d3d3d3',
        'green': 'good',
        'orange': 'warning',
        'red': 'danger',
        'purple': '#764FA5',
        'blue': '#439FE0'
    }

    text_color_dict = {
        'default': colors['grey'],
        'info': colors['grey'],
        'good': colors['green'],
        'green': colors['green'],
        'warn': colors['orange'],
        'orange': colors['orange'],
        'danger': colors['red'],
        'red': colors['red'],
        'purple': colors['purple'],
        'blue': colors['blue'],
    }

    if requested_color.lower() in map(unicode.lower, text_color_dict):
        return_color = text_color_dict[requested_color]
    else:
        print('ERROR - Invalid color: {}'.format(requested_color))
        print('Available colors: {}'.format(list(text_color_dict)))
        return_color = text_color_dict['default']
        print('Returning default color: '.format(return_color))

    return return_color
