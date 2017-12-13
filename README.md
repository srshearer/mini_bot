# pyBots  
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.

## slackAnnounce.py  

*Description:*
This script is for sending notification messages to Slack via webhooks. Send arbitrary messages as your bot user, send expected downtime, or server up notifications.

Before this will work, you will need to do the following…
1. Get a Slack webhook url. _(More info at: https://api.slack.com/incoming-webhooks)_
2. Rename _slack_config_example.py_ –> _slack_config.py_
3. Add the following information to _slack_config.py_
    - Your Slack webhook url
    - The default username you want to send messages as
    - The default Slack channel to send messages to
    - The Slack channel to send messages to when you are developint/testing/debugging
4. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that slack_config.py will not be pushed to git. This should already be set up properly for you.
  
*Required arguments:*  
`  -m, --message '<message>'` _Message to send to the channel._ `'up'` _will send a message (good/green) stating the server is back up._ `down <number> <time unit>, ex.'down 20 min'` _will send a message (warn/yellow) that the server will be going down for maintenance for that amount of time. Any other message will be sent as-is (info/gray)._  
  
*Optional arguments:*  
`  -h, --help`  _Show help message and exit_  
`  -c, --color <color>`  _Color for message. Color Options: gray/info (default), green/good, yellow/warn, red/danger, purple_  
`  -d, --debug`  _Enable debug mode. Send message to test channel and show json output in console._  
`  --dry`  _Enable dryrun mode. Message will not be sent._  
`  -r, --room <room>`  _Slack channel room to send the message to._  
`  -t, --title <title>`  _Set a message title._  
`  -u, --user <username>`  _Username of your bot to send message._  
`  --webhook <url>`  _Override default Slack webhook url._  


## plexBot.py

*Description:*
This script takes an IMDb movie guid as an argument to look for that movie in your Plex library. Information about the movie is gathered from the Plex library via PlexAPI and OMDb which is assembled into a json attatchment. This json attachment is used to send a new movie notification to Slack via slackAnnounce.py.

Before this will work, you will need to do the following…
1. Get _slackAnnounce.py_ up and running. _(See above)_
2. Rename _plex_config_example.py_ –> _plex_config.py_
3. Add the following information to _plex_config.py_
- Your Plex server name and URL
- Your Plex username and password
- Your OMDb api key _(Get this from http://www.omdbapi.com/apikey.aspx)_
4. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that plex_config.py will not be pushed to git. This should already be set up properly for you.
5. Install PlexAPI in order to interact with your Plex server. _(https://pypi.python.org/pypi/PlexAPI)_

*Recommended*
I would recommend that you install and use PlexPy on your Plex Server. This will not only give you a great web interface and statistics for your server and content, but will also allow you to monitor your server for new content and launch plexBot.py. Alternatively, you could use PlexPy to entirely circumvent the entire need of this script and just send Slack notifications via their built-in tools.

*Required arguments:*
`  -i, --guid '<IMDb guid>'` _The IMDb guid is required to look up the movie in your Plex library and to look up additional info from OMDb._  

*Optional arguments:*  
`  -h, --help`  _Show help message and exit_  
`  -d, --debug`  _Enable debug mode. Send message to test channel and show json output in console._  
`  --dry`  _Enable dryrun mode. Message will not be sent._  
