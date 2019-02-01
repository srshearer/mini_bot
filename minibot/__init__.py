import os.path
from minibot.utilities import config
from minibot.utilities import utils
logger = utils.Logger(file_path=os.path.abspath(config.LOG_FILE), stdout=True)
