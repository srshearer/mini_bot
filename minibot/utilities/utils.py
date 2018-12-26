#!/usr/bin/python -u
# encoding: utf-8
import math
import time
import os.path


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
            # this_file = os.path.basename(__file__).split(os.path.extsep)[0]
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

        print('Log file: {}'.format(os.path.abspath(file_path)))
        return file_path


def conv_millisec_to_min(milliseconds):
    """Requires int(milliseconds) and converts it to minutes.
    Returns: string(duration) (i.e. 117 min)
    """
    s, remainder = divmod(milliseconds, 1000)
    m, s = divmod(s, 60)
    minute_string = '{} min'.format(m)
    return minute_string


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
