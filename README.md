# minibot
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.

### plexBot.py

*Description:*
This is the primary script to interact with the collection of utility functions. Either send rich movie notifications to Slack, or send and receive notifications to transfer files between two servers.

###### *Usage examples:*
+ Send Slack message: 
    `python ./plexBot.py -i tt0168122`
+ Start server: 
    `python ./plexBot.py -s`
+ POST to server from client: 
    `python ./plexBot.py -i tt0168122 -p '~/Movies/Pirates of Silicon Valley (1999).mkv'`

###### *Arguments:* 

    -i, --guid '<IMDb guid>'    IMDb guid of the movie. Used to look up additional info from OMDb and to ensure a movie is only synced if it isn't already in the Plex library  
    -p '</path/to.file>'    Path to movie file

    -s    Start the server which will listen for new movie POSTs from the client

    -d, --debug    Enable debug mode. Send message to test channel and show more output in console.  
    --dry    Enable dryrun mode. Message will not be sent.  
    -h, --help    Show help message and exit


### Slack Notifier 

###### *Description:*

Takes a valid IMDb movie ID _(e.g. tt0168122)_ as an argument to search for that movie in your Plex library. Information about the movie is gathered from the Plex library via PlexAPI and OMDb which is assembled into a json attatchment. This json attachment is used to send a new movie notification to Slack via slackAnnounce.py.


### Plex Syncer: Client & Server

###### *Description:*

Runs a flask server which listens for at an endpoint for an imdb guid and a file path. When the endpoint receives a POST with this information, the file will be transferred from the remote machine to the local server if it is not already in a local Plex library. 


## Setup

Before this will work, you will need to do the following…
1. Get _slackAnnounce.py_ up and running. _(https://github.com/srshearer/slack-announce)_
2. Rename _plex_config_example.py_ –> _plex_config.py_
3. Add the following information to _plex_config.py_
    - Your Plex server name, username and password _(If you wish to use user auth)_
    - Your Plex token, server URL and port _(If you wish to use token auth)_
    - Your OMDb api key _(http://www.omdbapi.com/apikey.aspx)_
4. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that plex_config.py will not be pushed to git. This should already be set up properly for you.
5. Install PlexAPI in order to interact with your Plex server. _(https://pypi.python.org/pypi/PlexAPI)_

###### *Recommended*
- I would recommend that you install and use Tautulli on your Plex Server. This will not only give you a great web interface and statistics for your server and content, but will also allow you to monitor your server for new content and launch plexBot.py. Alternatively, you could use Tautulli to entirely circumvent the need of this script and just send Slack notifications via their built-in tools.
- Token based Plex authentication is set up by default but can be changed in plex_config.py. User based authentication is much slower than token based auth. 
