#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import pysftp
from Queue import Queue
from mini_bot.minibot import logger
from mini_bot.minibot.utilities import utils
from mini_bot.minibot.utilities import plexutils
from mini_bot.minibot.utilities import config
from slackannounce.utils import SlackSender


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
        self.max_concurrent_transfers = 1

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
            self.logger.info('Copying from remote server: {}@{}:\'{}\''.format(
                self.remote_user, self.remote_server, self.remote_file))
            self.logger.debug('Temp destination: {}'.format(self._tmp_dir))
            success = self._transfer_file()
            if success:
                self._move_file_to_destination()
                print('Transfer successful: {}'.format(
                    self.transfer_successful))

        return self.transfer_successful, self.final_file_path

    @utils.retry(logger=logger)
    def _transfer_file(self):
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
            self.logger.error(
                'File transfer failed: {} \n{}'.format(self.filename, e))
            raise

        if self.transfer_successful:
            self.logger.info('Transfer successful!')

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


class PlexSyncer(object):
    def __init__(self, imdb_guid=None, remote_path=None, debug=False,
                 logger=logger, **kwargs):
        self.kwargs = kwargs
        self.debug = debug
        self.imdb_guid = imdb_guid
        self.remote_path = remote_path
        self.title_year = None
        self.movie_dir = os.path.expanduser(config.FILE_TRANSFER_COMPLETE_DIR)
        self.plex_local = None
        self.logger = logger

    def connect_plex(self):
        self.logger.info('Connecting to Plex')
        self.plex_local = plexutils.PlexSearch(
            debug=self.debug,
            auth_type=config.PLEX_AUTH_TYPE,
            server=config.PLEX_SERVER_URL
        )
        self.plex_local.connect()

        return

    def notify_slack(self, message, room='me'):
        self.logger.info(message)
        notification = SlackSender(room=room, debug=self.debug)
        notification.set_simple_message(
            message=message, title='Plex Syncer Notification')
        notification.send()

    def get_title_year(self, imdb_guid=None):
        if not imdb_guid:
            imdb_guid = self.imdb_guid
        status, result = plexutils.omdb_guid_search(
            imdb_guid=imdb_guid)
        try:
            title_year = '{} ({})'.format(result["Title"], result["Year"])
        except Exception:
            title_year = None

        return title_year

    def run_sync_flow(self):
        self.connect_plex()
        self.title_year = self.get_title_year()
        if not self.plex_local.in_plex_library(guid=self.imdb_guid):
            message = 'Movie not in library: [{}] {} - {}'.format(
                self.imdb_guid, self.title_year, self.remote_path)
            self.notify_slack(message)

            syncer = FileSyncer(
                remote_file=self.remote_path,
                destination=self.movie_dir)
            success, file_path = syncer.get_remote_file()

            if not file_path or not success:
                message = 'Transfer failed: {}'.format(message)
                self.logger.error(message)
            else:
                message = 'Download complete: {} - {}'.format(
                    self.title_year, file_path)
            self.notify_slack(message)
        else:
            success = True
            self.logger.info('Movie already in library: [{}] {}\n{}'.format(
                self.imdb_guid, self.title_year, self.remote_path))

        return success


class TransferQueue(object):
    def __init__(self, db):
        self.queue = Queue()
        self.db = db

    def _worker(self):
        while not self.queue.empty():
            logger.info('Queued items: {}'.format(self.queue.unfinished_tasks))
            q_guid = self.queue.get()
            logger.info('Starting download: {}'.format(q_guid))
            queued_movie_dict = self.db.row_to_dict(self.db.select_guid(q_guid))
            logger.debug('Starting: {}'.format(q_guid))
            syncer = PlexSyncer(
                imdb_guid=q_guid,
                remote_path=queued_movie_dict['remote_path']
            )
            successful = syncer.run_sync_flow()
            if successful:
                self.db.mark_complete(q_guid)
            else:
                self.db.mark_unqueued_incomplete(q_guid)

            self.queue.task_done()
            logger.info('Completed download: {}'.format(q_guid))

        logger.debug('Queue empty')
        return

    def add_item(self, guid, **kwargs):
        logger.debug('Enqueuing: {}'.format(guid))
        self.queue.put(guid, **kwargs)
        self.db.mark_queued(guid)

    def start(self):
        if not self.queue.empty():
            self._worker()

        return


def transfer_queue_loop(db):
    ''' Instantiate the TransferQueue using the supplied database, then
    continuously check for unqueued items in the database, add them to the
    queue, and empty the queue.
    :param db:
    :return:
    '''
    cont = True
    q = TransferQueue(db)
    while cont:
        try:
            unqueued = db.select_all_unqueued_movies()
            for unqueued_row in unqueued:
                unqueued_dict = db.row_to_dict(unqueued_row)
                guid = unqueued_dict['guid']
                q.add_item(guid)

            q.start()
            time.sleep(10)
            # cont = False

        except KeyboardInterrupt:
            incomplete_rows = db.select_all_queued_incomplete()

            for i in incomplete_rows:
                guid = db.row_to_dict(i)['guid']
                logger.debug('guid: {} - row: {}'.format(guid, i))
                db.mark_unqueued_incomplete(guid)

            sys.exit(0)
