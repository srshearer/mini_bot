#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import json
import requests


class SlackException(Exception):
    """Custom exception for Slack related failures."""
    pass


class SlackSender(object):
    def __init__(self, webhook_url=None, channel=None, user=None,
                 json_attachments=None, debug=False, dryrun=False):
        self.debug = debug
        self.dryrun = dryrun
        self.webhook_url = webhook_url
        self.json_attachments = json_attachments
        self.user = user
        self.channel = channel
        self.color = text_color('info')
        self._json_payload = None

    def set_simple_message(self, message, title=None,
                           color=None, fallback=None):
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

        if not color:
            color = self.color

        if not fallback:
            fallback = title or message

        self.json_attachments = {
            "fallback": fallback,
            "color": color,
            "text": message,
        }

        if title:
            self.json_attachments["title"] = title

        return self.json_attachments

    def send(self):
        """Send the Slack notification with the current json_attachments.
        This will update the debug state, channel, and webhook before sending.
        """
        if not self.user:
            raise SlackException('Missing user')
        if not self.webhook_url:
            raise SlackException('Missing webhook url')
        if not self.json_attachments:
            raise SlackException('json_attachments not set')

        self._json_payload = {
            "channel": self.channel,
            "username": self.user,
            "attachments": [
                self.json_attachments
            ]
        }

        if self.debug:
            print('json payload: {}'.format(self._json_payload))

        if self.dryrun:
            print('[Dry run. Not posting message.]')
            return

        response = requests.post(
            self.webhook_url, data=json.dumps(self._json_payload),
            headers={'Content-Type': 'application/json'}
        )
        print('Result: [{}] {}'.format(response.status_code, response.text))

        return response


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
