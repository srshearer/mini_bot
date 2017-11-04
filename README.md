# pyBots  
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.

## slackAnnounce.py  
Before this will work, you will need to do the following…
1. Get a Slack webhook url. _(More info at: https://api.slack.com/incoming-webhooks)_
2. Rename _renametosecrets.py_ –> _secrets.py_  
3. Add the following information to _secrets.py_
    - Your Slack webhook url
    - The default username you want to send messages as
    - The default Slack channel to send messages to
    - The Slack channel to send messages to when you are developint/testing/debugging
4. Verify that _.gitignore_ lists _secrets.py_ as an ignored file and will not be pushed to git. This should already be set up properly for you.  
  
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
