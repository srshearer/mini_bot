# minibot
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.


## plexBot.py

*Description:*
This script takes an IMDb movie guid as an argument to look for that movie in your Plex library. Information about the movie is gathered from the Plex library via PlexAPI and OMDb which is assembled into a json attatchment. This json attachment is used to send a new movie notification to Slack via slackAnnounce.py.

Before this will work, you will need to do the following…
1. Get _slackAnnounce.py_ up and running. _(See above)_
2. Rename _plex_config_example.py_ –> _plex_config.py_
3. Add the following information to _plex_config.py_
    - Your Plex server name, username and password _(If you wish to use user auth)_
    - Your Plex token, server URL and port _(If you wish to use token auth)_
    - Your OMDb api key _(http://www.omdbapi.com/apikey.aspx)_
4. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that plex_config.py will not be pushed to git. This should already be set up properly for you.
5. Install PlexAPI in order to interact with your Plex server. _(https://pypi.python.org/pypi/PlexAPI)_

*Recommended*
- I would recommend that you install and use Tautulli on your Plex Server. This will not only give you a great web interface and statistics for your server and content, but will also allow you to monitor your server for new content and launch plexBot.py. Alternatively, you could use Tautulli to entirely circumvent the need of this script and just send Slack notifications via their built-in tools.
- Token based Plex authentication is set up by default but can be changed in plex_config.py. User based authentication is much slower than token based auth. 

*Required arguments:*
`  -l`  _Start server and listen for new movie sync notifications_

`  -i, --guid '<IMDb guid>'` _IMDb guid of the movie. Used to look up additional info from OMDb and to ensure a movie is only synced if it isn't already in the Plex library_
`  -p`  _Path to movie file_

`  -h, --help`  _Show help message and exit_
`  -d, --debug`  _Enable debug mode. Send message to test channel and show json output in console._  
`  --dry`  _Enable dryrun mode. Message will not be sent._  



## plexSyncer.py

*Description:*
plexSyncer runs a flask server which listens for at an endpoint for an imdb guid and a filepath. When the endpoint it hit with this information, the file will be transferred to the local server if it is not already in a local Plex library. 

Before this will work, you will need to do the following…
1. Get _slackAnnounce.py_ up and running _(https://github.com/srshearer/slack-announce)_
2. Rename _config_example.py_ –> _config.py_ and add the required infromation_
3. Verify that _.gitignore_ lists _*config.py_ as an ignored file and that plex_config.py will not be pushed to git
4. Run Setup.py to install the script and its dependencies

*Recommended*
- I would recommend that you install and use Tautulli on your Plex Server. This will not only give you a great web interface and statistics for your server and content, but will also allow you to monitor your server for new content and launch plexBot.py. Alternatively, you could use Tautulli to entirely circumvent the need of this script and just send Slack notifications via their built-in tools.
- Token based Plex authentication is set up by default but can be changed in config.py. User based authentication is much slower than token based auth. 

*Required arguments:*
`  -i, --guid '<IMDb guid>'` _The IMDb guid is required to look up the movie in your Plex library and to look up additional info from OMDb._  

*Optional arguments:*  
`  -h, --help`  _Show help message and exit_  
`  -d, --debug`  _Enable debug mode. Send message to test channel and show json output in console._  
`  -n`  _Notify remote server of new movie. Note that this requires both `-i` and `-p` be set__  
`  -i`  _IMdB guid of the movie_  
`  -p`  _Path to local movie file_  
