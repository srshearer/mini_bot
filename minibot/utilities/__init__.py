import os.path
import signal

from utilities import config
from utilities import utils
from utilities.utils import Logger

logfile = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOG_FILE))
logger = Logger(file_path=logfile, stdout=True)

signal.signal(signal.SIGINT, utils.interrupt_handler)
signal.signal(signal.SIGTERM, utils.interrupt_handler)
