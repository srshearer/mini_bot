#!/usr/bin/env python3
import os.path

from utilities import config
from utilities import dbutils
from utilities import utils
from utilities.utils import Logger

logfile = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOG_FILE))
logger = Logger(file_path=logfile, stdout=True)

db = dbutils.FileTransferDB()
