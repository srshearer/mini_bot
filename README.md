# minibot
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.


### plexBot.py

This is the primary script to interact with the collection of utility functions. Either send rich movie notifications to Slack, or send and receive notifications to transfer files between two servers.

###### *Usage examples:*
+ Plex Syncer: Server | _Start flask server_:
    `mini_bot/venv/bin/mod_wsgi-express start-server --reload-on-changes ./minibotserver.wsgi --port 5000`
+ Plex Syncer: Server | _Start file sync:_ 
    `python ./plexBot.py -s`
+ Plex Syncer: Client | _POST to server from client_: 
    `python ./plexBot.py -i tt0168122 -p '~/Movies/Pirates of Silicon Valley (1999).mkv'`
+ Slack Notifier: Server | _Send Slack message:_ 
    `python ./plexBot.py -i tt0168122`

###### *Arguments:* 

    -i, --guid '<IMDb guid>'  IMDb guid of the movie. Used to look up additional 
                              info from OMDb and to ensure a movie is only 
                              synced if it isn't already in the Plex library  

    -p '</path/to.file>'      Path to movie file

    --pathonly                Path to movie file

    -s                        Start the file syncer

    -d, --debug               Enable debug mode. Send message to test channel 
                              and show more output in console.  
    --dry                     Enable dryrun mode. Message will not be sent.  

    -h, --help                Show help message and exit


### Slack Notifier 

Takes a valid IMDb movie ID _(e.g. tt0168122)_ as an argument to search for that movie in your Plex library. Information about the movie is gathered from the Plex library via PlexAPI and OMDb which is assembled into a json attatchment. This json attachment is used to send a new movie notification to Slack via a provided webhook url.


### Plex Syncer: Client & Server

Runs a flask server which listens for at an endpoint for an imdb guid and a file path. When the endpoint receives a POST with this information, the file will be transferred from the remote machine to the local server if it is not already in a local Plex library. 


# Setup

Before this will work, you will need to do the following…
1. Create a copy of _config_example.py_ and rename it _config.py_
2. Add the following information to _config.py_
    - Your Plex server name, username and password _(If you wish to use user auth)_
    - Your Plex token, server URL and port _(If you wish to use token auth)_
    - Your Slack webhook url, channel, bot username _(If you wish to use token auth)_
    - Your [OMDb api key](http://www.omdbapi.com/apikey.aspx)
3. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that config.py will not be pushed to git _(This should already be set up properly for you)_  
4. Install requirements from requirements.txt  

###### *Recommendations*
- I would recommend that you install and use [Tautulli](https://tautulli.com) on your Plex Server. This will not only give you a great web interface and statistics for your server and content, but will also allow you to monitor your server for new content and launch plexBot.py. Alternatively, you could use Tautulli to entirely circumvent the need of this script and just send Slack notifications via their built-in tools.
- Token based Plex authentication is set up by default but can be changed in config.py. User based authentication is much slower than token based auth. 

###### *Requirements:* 
+ Python 3.7+
+ PlexAPI
+ Flask
+ pysftp
+ paramiko
+ Slack webhook url
+ Plex & Plex auth token
+ OMDb api key

###### *Links*
+ Plex: https://www.plex.tv
+ PlexAPI: https://pypi.python.org/pypi/PlexAPI
+ OMDb API: http://www.omdbapi.com/apikey.aspx
+ Tautulli: https://tautulli.com
