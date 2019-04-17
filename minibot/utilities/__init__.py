import os.path
from minibot.utilities import config
from minibot.utilities.utils import Logger

logfile = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOG_FILE))
logger = Logger(file_path=logfile, stdout=True)
