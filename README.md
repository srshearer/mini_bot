# pyBots
Python tools for sending messages to Slack and interfacing with Plex. Created for my personal use.

* slackAnnounce.py
Before this will work, you will need to do the following…
1. Get a Slack webhook url. More info at: https://api.slack.com/incoming-webhooks
2. Add the following information to renametosecrets.py
  - Your Slack webhook url
  - The default username you want to send messages as
  - The default Slack channel to send messages to
  - The Slack channel to send messages to when you are developint/testing/debugging
3. Rename renametosecrets.py –> secrets.py
4. Verify that .gitignore lists secrets.py as an ignored file
