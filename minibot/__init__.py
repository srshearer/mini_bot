import sys
import os.path
# import logging
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from mini_bot.minibot.utilities import config
from mini_bot.minibot.utilities import utils

logfile = os.path.abspath(
    os.path.join(os.path.dirname(__file__), config.LOG_FILE))

logger = utils.Logger(file_path=logfile, stdout=True)

# logFormatter = '%(asctime)s: %(levelname)s: %(message)s'
# "%(levelname)s:%(name)s:%(message)s"
# logging.basicConfig(format=logFormatter, level=logging.DEBUG)
#
# logger = logging.getLogger(config.LOG_FILE)
# handler = logging.FileHandler(logfile)
# handler.setLevel(logging.DEBUG)
# logger.addHandler(handler)
logger.info('logfile: {}'.format(logfile))
