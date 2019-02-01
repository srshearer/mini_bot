#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import pysftp
from minibot import logger
from minibot.utilities import utils
from minibot.utilities import config


class FileSyncer(object):
    def __init__(self, remote_file=None,
                 destination=config.FILE_TRANSFER_COMPLETE_DIR):
        self.remote_server = config.REMOTE_FILE_SERVER
        self.remote_user = config.REMOTE_USER

        self.remote_file = remote_file
        self.filename = None
        self.final_file_path = None

        self._in_progress_file = None
        self._tmp_dir = os.path.expanduser(config.IN_PROGRESS_DIR)
        self.destination_dir = os.path.expanduser(destination)

        self.logger = logger
        self.transfer_successful = False

        self._local_prv_key = os.path.expanduser(
            os.path.join("~/.ssh", "id_rsa"))

        self._seen_progress = []
        self._transfer_start_time = None
        self._transfer_end_time = None
        self._prev_completed_bytes = 0
        self._prev_progress_time = None

    def _set_file_paths(self, remote_file=None):
        if remote_file:
            self.remote_file = remote_file

        if not self.remote_file:
            self.logger.error('No remote file!', stdout=True)
            sys.exit(1)

        self.filename = os.path.basename(self.remote_file)
        self.final_file_path = os.path.join(
            self.destination_dir, self.filename)

        return self.remote_file

    def get_remote_file(self):
        if not self.remote_file:
            self.logger.error(
                'Remote file not set! Please set FileSyncer.remote_file')
        else:
            self._set_file_paths(self.remote_file)
            success = self._transfer_file()
            if success:
                self._move_file_to_destination()
                print('Transfer successful: {}'.format(
                    self.transfer_successful))

        return self.transfer_successful, self.final_file_path

    def _transfer_file(self):
        self.logger.info('Copying from remote server: {}@{}:\'{}\''.format(
            self.remote_user, self.remote_server, self.remote_file))
        self.logger.debug('Temp destination: {}'.format(self._tmp_dir))

        try:
            self._in_progress_file = os.path.join(
                self._tmp_dir, 'IN_PROGRESS-' + self.filename)
            with pysftp.Connection(self.remote_server,
                                   username=self.remote_user,
                                   private_key=self._local_prv_key) as sftp:
                self._transfer_start_time = time.time()
                sftp.get(self.remote_file, self._in_progress_file,
                         callback=self._transfer_progress)

        except Exception as e:
            self.transfer_successful = False
            msg = 'Error getting file: {} \n{}'.format(self.filename, e)
            self.logger.error('{}'.format(msg))
            raise

        if self.transfer_successful:
            msg = 'Transfer successful!'
            self.logger.info('{}'.format(msg))

        return self.transfer_successful

    def _move_file_to_destination(self):
        """
        Move file from in progress directory into its final destination
        directory.
        :return:
        """
        if os.path.isfile(self._in_progress_file):
            try:
                self.logger.info('Moving {} to {}'.format(
                    self.filename, self.destination_dir))
                if not os.path.isdir(self.destination_dir):
                    os.mkdir(self.destination_dir)

                os.rename(self._in_progress_file, self.final_file_path)

            except OSError as e:
                self.logger.error('Failed to move file \n{}'.format(e))
                self.final_file_path = None
        else:
            self.final_file_path = None

        return self.final_file_path

    def _remove_file(self):
        if os.path.exists(os.path.join(self._tmp_dir, self.filename)):
            os.remove(os.path.join(self._tmp_dir, self.filename))

    def _transfer_progress(self, complete, total, step=1):
        """
        Calculate and log the percent of the file that has been transferred as
        well as the transfer rate.
        :param complete: (int) bytes transferred
        :param total: (int) total bytes
        :param step: (int) what percentages to log. example: step of 5 would log
            every 5 percent of file completion: 0%, 5%, 10% … 100%
        :return:
        """
        pct = 100 * complete / total
        c = utils.convert_file_size(complete)
        t = utils.convert_file_size(total)

        # log each N percentage exactly once where in is step
        if pct in range(101)[0::step] and pct not in self._seen_progress:
            rate = utils.convert_file_size(self._transfer_rate(complete))
            self.logger.info(
                'Transfer Progress: {}\t{}%  \t[ {} / {} ]\t{}/s'.format(
                    self.filename, pct, c, t, rate))
            self._seen_progress.append(pct)

        # transfer complete
        if pct == 100:
            self._transfer_end_time = time.time()
            self.transfer_successful = True
            duration = abs(
                (self._transfer_end_time - self._transfer_start_time))
            rate = utils.convert_file_size((total / duration))
            self.logger.info(
                'Transfer completed in {} seconds [{}/s]'.format(
                    round(duration, 2), rate))

    def _transfer_rate(self, complete):
        """
        Return the transfer rate in bytes per second based on the number of
        bytes already transferred.
        :param complete: (int) bytes transferred so far
        :return: transfer_rate (float) bytes per second
        """
        now = time.time()
        if not self._prev_progress_time:
            self._prev_progress_time = self._transfer_start_time

        byte_progress = abs((complete - self._prev_completed_bytes))
        time_progress = abs((now - self._prev_progress_time))
        transfer_rate = (byte_progress / time_progress)

        self._prev_progress_time = now
        self._prev_completed_bytes = complete

        return transfer_rate
