"""
This is a config file for holding keys, tokens, webhooks, and other private
info. This file will be in your .gitignore file once renamed.
You MUST rename this file to slack_config.py in order for slackAnnounce.py to
function.
"""
SLACK_WEBHOOK_URL = '<YOUR SLACK WEBHOOK URL>'
SLACK_WEBHOOK_URL_ME = '<SLACK WEBHOOK URL TO SEND MESSAGES TO YOURSELF>'
DEFAULT_SLACK_USER = '<YOUR DEFAULT USERNAME TO SEND MESSAGES AS>'
DEFAULT_SLACK_ROOM = '<DEFAULT CHANNEL TO SEND MESSAGE TO>'
DEBUG_SLACK_ROOM = '<DEFAULT CHANNEL TO SEND MESSAGE TO FOR DEV/DEBUG PURPOSES>'
SLACK_BOT_TOKEN = '<YOUR SLACK BOT TOKEN>'
DEFAULT_TITLE = 'Server Announcement: '
