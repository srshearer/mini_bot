"""
This is a config file for holding keys, tokens, webhooks, and other private
info. This file will be in your .gitignore file once renamed.
You MUST rename this file to config.py in order for these scripts to function.
"""

LOG_FILE = './plexbot.log'  # Log file location. No need to change this.
OMDB_API_KEY = '<YOUR OMDB API KEY>'  # Get this from: http://www.omdbapi.com/apikey.aspx


## Plex Config ##
PLEX_AUTH_TYPE = 'token'   # 'token' or 'user
PLEX_SERVER_URL = ''   # <YOUR PLEX SERVER URL>'

# User Auth:
PLEX_SERVER_NAME = ''   # <YOUR PLEX SERVER NAME>
PLEX_USERNAME = ''   # <YOUR PLEX USERNAME>
PLEX_PASSWORD = ''   # <YOUR PLEX PASSWORD>

# Token Auth:
PLEX_TOKEN = ''   # <YOUR PLEX TOKEN>


## Syncer Configs ##

# Client / Notifier:
REMOTE_LISTENER = ''   # <'ip:port' - Remote server to inform of new movies>

# Server / Listener:
REMOTE_FILE_SERVER = ''   # <Remote server ip>
REMOTE_USER = ''   # <user for remote server>
IN_PROGRESS_DIR = '~/Downloads/'   # <path for in progress downloads>
FILE_TRANSFER_COMPLETE_DIR = '~/Downloads/'   # <final destination path for downloads>


## Slack Config ##

SLACK_WEBHOOK_URL = '<YOUR SLACK WEBHOOK URL>'
SLACK_WEBHOOK_URL_ME = '<SLACK WEBHOOK URL TO SEND MESSAGES TO YOURSELF>'
DEFAULT_SLACK_USER = '<YOUR DEFAULT USERNAME TO SEND MESSAGES AS>'
DEFAULT_SLACK_ROOM = '<DEFAULT CHANNEL TO SEND MESSAGE TO>'
DEBUG_SLACK_ROOM = '<DEFAULT CHANNEL TO SEND MESSAGE TO FOR DEV/DEBUG PURPOSES>'
SLACK_BOT_TOKEN = '<YOUR SLACK BOT TOKEN>'
DEFAULT_TITLE = 'Server Announcement: '
