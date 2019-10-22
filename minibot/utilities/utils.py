#!/usr/bin/python3 -u
# encoding: utf-8
import math
import time
import os.path
import functools
import threading


class Logger(object):
    def __init__(self, file_path=None, stdout=False):
        self._file_path = self._create_log_file(file_path=file_path)
        self._stdout = stdout

    @property
    def file_path(self):
        return self._file_path

    def critical(self, message, stdout=False):
        self._log(message, 'CRITICAL', stdout)

    def error(self, message, stdout=False):
        self._log(message, 'ERROR', stdout)

    def warning(self, message, stdout=False):
        self._log(message, 'WARNING', stdout)

    def info(self, message, stdout=False):
        self._log(message, 'INFO', stdout)

    def debug(self, message, stdout=False):
        self._log(message, 'DEBUG', stdout)

    def _log(self, message, log_type, stdout=False):
        log_line = self._log_formatter(message, log_type)
        self._append_to_log(log_line)
        if stdout or self._stdout:
            print(log_line.rstrip())

    @staticmethod
    def _log_formatter(message, msg_type):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = u'{} {}: {}\n'.format(
            ts, msg_type, message, encoding='utf-8')

        return log_line

    def _append_to_log(self, log_line):
        with open(self._file_path, 'a') as log:
            log.write(log_line)

    @staticmethod
    def _create_log_file(file_path=None):
        if not file_path:
            file_name = 'log{}log'.format(os.path.extsep)
            dir_path = os.path.abspath('.')
            file_path = os.path.join(dir_path, file_name)
        else:
            file_path = os.path.expanduser(file_path)
            dir_path = os.path.dirname(file_path) or os.path.abspath('.')

        if not os.path.isfile(file_path):
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except IOError as e:
                    raise IOError(
                        'Path does not exist and could not be created: '
                        '{} \n{}'.format(dir_path, e))
            else:
                try:
                    open(file_path, 'a').close()
                except IOError as e:
                    raise IOError('Could not create file: '
                                  '{} \n{}'.format(file_path, e))

        return file_path


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def conv_millisec_to_min(milliseconds):
    """Requires int(milliseconds) and converts it to minutes.
    Returns: int(minutes)
    """
    s, remainder = divmod(milliseconds, 1000)
    m, s = divmod(s, 60)

    return m


def convert_file_size(size_bytes):
    """Converts file size in bytes as to human readable format.
    Requires:
        - int(bytes)
    Returns:
        - string (i.e. 3.21 GB)
    """
    if size_bytes == 0:
        return '0B'
    size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return '{} {}'.format(s, size_name[i])


def retry(attempts=3, exception_to_check=Exception,
          delay=3, backoff=2, logger=None):
    """Retry decorator to call function up to specified number of times in
    case of specified exception. """

    def decorator(func):
        @functools.wraps(func)
        def func_retry(*args, **kwargs):
            this_attempts, this_delay = attempts, delay
            while this_attempts > 0:
                try:
                    return func(*args, **kwargs)
                except exception_to_check as e:
                    message = 'Exception: {}, Retrying in {} seconds...'.format(
                        str(e), this_delay)
                    if logger:
                        logger.warning(message)
                    else:
                        print(message)
                    time.sleep(this_delay)
                    this_attempts -= 1
                    this_delay *= backoff
            return func(*args, **kwargs)

        return func_retry

    return decorator


class SigInt(Exception):
    pass


def interrupt_handler(sig, frame):
    msg = 'Received signal: {}'.format(str(sig))
    raise SigInt(msg)
