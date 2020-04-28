#!/usr/bin/env python3
import os
import time
import signal
from queue import Queue

import pysftp

from utilities import config
from utilities import db
from utilities import logger
from utilities import omdb
from utilities import plexutils
from utilities import utils
from utilities.plexutils import PlexException
from utilities.slackutils import SlackSender
from utilities.utils import retry
from utilities.utils import SigInt


signal.signal(signal.SIGINT, utils.interrupt_handler)
signal.signal(signal.SIGTERM, utils.interrupt_handler)


def notify_slack(message, title=None, channel="me", debug=False):
    if not title:
        title = "Plex Syncer Notification"

    if channel == "me":
        webhook_url = config.SLACK_WEBHOOK_URL_ME
        channel = None
    else:
        webhook_url = config.SLACK_WEBHOOK_URL

    logger.info(f"Sending Slack notification: {title} | {message}")

    notification = SlackSender(
        webhook_url=webhook_url,
        user=config.DEFAULT_SLACK_USER,
        channel=channel,
        debug=debug
    )
    notification.set_simple_message(message=message, title=title)
    notification.send()


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
            logger.error("No remote file!", stdout=True)
            return None

        self.filename = os.path.basename(self.remote_file)
        self.final_file_path = os.path.join(
            self.destination_dir, self.filename)

        return self.remote_file

    def get_remote_file(self):
        success = False
        if not self.remote_file:
            logger.error(
                "Remote file not set! Please set FileSyncer.remote_file")
        else:
            self._set_file_paths(self.remote_file)
            logger.info(f"Copying from remote server: "
                        f"{self.remote_user}@{self.remote_server}:"
                        f"\"{self.remote_file}\"")
            logger.debug(f"Temp destination: {self._tmp_dir}")
            try:
                success = self._transfer_file()
            except Exception as e:
                logger.error(f"Transfer failed after 3 attempts: {e}")
                pass

            if success:
                self._move_file_to_destination()
                print(f"Transfer successful: {self.transfer_successful}")

        return self.transfer_successful, self.final_file_path

    @utils.retry(attempts=3, delay=10, logger=logger)
    def _transfer_file(self):
        logger.info("Starting file transfer...")
        self.transfer_successful = False
        try:
            self._in_progress_file = os.path.join(
                self._tmp_dir, "IN_PROGRESS-" + self.filename)
            with pysftp.Connection(self.remote_server,
                                   username=self.remote_user,
                                   private_key=self._local_prv_key) as sftp:
                self._transfer_start_time = time.time()
                sftp.get(self.remote_file, self._in_progress_file,
                         callback=self._transfer_progress)

        except Exception:
            raise

        if self.transfer_successful:
            logger.info("Transfer successful!")

        return self.transfer_successful

    def _move_file_to_destination(self):
        """
        Move file from in progress directory into its final destination
        directory.
        :return:
        """
        if os.path.isfile(self._in_progress_file):
            try:
                logger.info(
                    f"Moving {self.filename} to {self.destination_dir}")
                if not os.path.isdir(self.destination_dir):
                    os.mkdir(self.destination_dir)

                os.rename(self._in_progress_file, self.final_file_path)

            except OSError as e:
                logger.error(f"Failed to move file \n{e}")
                self.final_file_path = None

            try:
                if self.final_file_path:
                    logger.debug("Setting file permissions")
                    file_stat_before = os.stat(self.final_file_path)
                    file_mode_before = file_stat_before.st_mode
                    logger.debug(
                        f"File permissions before: {file_mode_before}")

                    os.chmod(
                        self.final_file_path, config.SYNCED_FILE_PERMISSIONS)

                    file_stat_after = os.stat(self.final_file_path)
                    file_mode_after = file_stat_after.st_mode
                    logger.debug(f"File permissions after: {file_mode_after}")

                else:
                    logger.error("No file path!")

            except Exception as e:
                logger.error(f"Failed to set file permissions: {str(e)}")

        else:
            self.final_file_path = None

        return self.final_file_path

    def _transfer_progress(self, complete, total, step=1):
        """
        Calculate and log the percent of the file that has been transferred
        as well as the transfer rate.
        :param complete: (int) bytes transferred
        :param total: (int) total bytes
        :param step: (int) what percentages to log. example: step of 5 would
        log every 5 percent of file completion: 0%, 5%, 10% … 100%
        :return:
        """
        pct = round(100 * complete / total)
        c = utils.convert_file_size(complete)
        t = utils.convert_file_size(total)

        # log each N percentage exactly once where in is step
        if pct in range(101)[0::step] and pct not in self._seen_progress:
            rate = utils.convert_file_size(self._transfer_rate(complete))
            logger.info(f"Transfer Progress: {self.filename}\t{pct}%  \t[ {c} / {t} ]\t{rate}/s")
            self._seen_progress.append(pct)

        # transfer complete
        if pct == 100:
            self._transfer_end_time = time.time()
            self.transfer_successful = True
            duration = abs(
                self._transfer_end_time - self._transfer_start_time)
            rate = utils.convert_file_size(total / duration)
            logger.info(f"Transfer completed in "
                        f"{round(duration, 2)} seconds [{rate}/s]")

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

        byte_progress = abs(complete - self._prev_completed_bytes)
        time_progress = abs(now - self._prev_progress_time)
        transfer_rate = (byte_progress / time_progress)

        self._prev_progress_time = now
        self._prev_completed_bytes = complete

        return transfer_rate


class PlexSyncer(object):
    def __init__(self, imdb_guid=None, remote_path=None,
                 debug=False, **kwargs):
        self.kwargs = kwargs
        self.debug = debug
        self.imdb_guid = imdb_guid
        self.remote_path = remote_path
        self.title_year = None
        self.movie_dir = os.path.expanduser(config.FILE_TRANSFER_COMPLETE_DIR)
        self.plex_local = None
        self._omdb = omdb.OMDb(api_key=config.OMDB_API_KEY, debug=debug)

    @utils.retry(delay=30, exception_to_check=plexutils.PlexException)
    def connect_plex(self):
        logger.info("Connecting to Plex")
        self.plex_local = plexutils.PlexSearch(
            debug=self.debug,
            auth_type=config.PLEX_AUTH_TYPE,
            server=config.PLEX_SERVER_URL
        )
        self.plex_local.connect()

        return

    def get_title_year(self, imdb_guid=None):
        if not imdb_guid:
            imdb_guid = self.imdb_guid

        result, status = self._omdb.search(imdb_guid=imdb_guid)

        logger.debug(f"Response from OMDb: [{status}] {result}")
        if not status == 200:
            logger.error(
                f"Non-200 response from OMDb: [{status}] {result}")
            return None

        try:
            title_year = f"{result['Title']} ({result['Year']})"
            logger.debug(f"Title and year: {title_year}")
        except Exception as e:
            logger.error(f"Failed to determine title and year: {str(e)}")
            return None

        return title_year

    def run_sync_flow(self):
        self.connect_plex()
        self.title_year = self.get_title_year()
        if not self.plex_local.in_plex_library(guid=self.imdb_guid):
            message = f"Movie not in library: [{self.imdb_guid}] " \
                      f"{self.title_year} - {self.remote_path}"
            t = f"New transfer: {self.title_year}"
            notify_slack(message, title=t, debug=self.debug)

            syncer = FileSyncer(
                remote_file=self.remote_path,
                destination=self.movie_dir)

            file_path = None
            try:
                success, file_path = syncer.get_remote_file()
            except Exception as e:
                logger.warning(
                    f"Skipping item due to exception: "
                    f"{self.imdb_guid} \n{str(e)}")
                success = False

            if not file_path or not success:
                t = f"Transfer failed: {self.title_year}"
                message = f"Transfer failed: {self.title_year}"
                logger.error(message)
            else:
                t = f"Download complete: {self.title_year}"
                message = f"Download complete: {self.title_year} - {file_path}"
            notify_slack(message, title=t, debug=self.debug)
        else:
            success = False

            logger.info(f"Movie already in library: [{self.imdb_guid}]"
                        f"{self.title_year}\n{self.remote_path}")

        return success


class TransferQueue(object):
    def __init__(self, database, *args, **kwargs):
        self.queue = Queue()
        self.db = database

    def _worker(self):
        while not self.queue.empty():
            logger.info("Queued items: {}".format(self.queue.unfinished_tasks))
            q_guid = self.queue.get()
            logger.info(f"Starting download: {q_guid}")
            queued_movie = self.db.select_guid(q_guid)
            syncer = PlexSyncer(
                imdb_guid=q_guid,
                remote_path=queued_movie['remote_path']
            )
            successful = syncer.run_sync_flow()
            if successful:
                self.db.mark_complete(q_guid)
                logger.info(f"Completed download: {q_guid}")
            else:
                self.db.remove_guid(q_guid)
                logger.error(f"Failed download: {q_guid}")

            self.queue.task_done()

        return

    def add_item(self, guid, **kwargs):
        logger.debug(f"Enqueuing: {guid}")
        self.queue.put(guid, **kwargs)
        self.db.mark_queued(guid)

    @retry(exception_to_check=PlexException,
           delay=30, logger=logger)
    def run(self, update_frequency=5):
        """ Instantiate the TransferQueue using the supplied database, then
        continuously check for unqueued items in the database, add them to the
        queue, and empty the queue.
        :param update_frequency: How frequently in seconds to check the db
            for items. (defaults to 5 seconds)
        :return:
        """
        u = None
        try:
            while True:
                unqueued = self.db.select_all_unqueued_movies()
                for u in unqueued:
                    self.add_item(u['guid'])

                if self.queue.empty():
                    time.sleep(update_frequency)
                else:
                    self._worker()

        except SigInt as e:
            logger.debug(e)
            logger.debug("Exiting queue: SigInt")

        except Exception as e:
            t = f"Transfer exception: {u}"
            msg = f"Exiting queue: Exception! Failed item: " \
                  f"{tuple(u)}"
            logger.error(e)
            logger.warning(msg)
            notify_slack(message=e, title=t)
            notify_slack(message=msg, title=t)

            logger.debug("Exiting queue: Unknown Exception")
            raise PlexException(e)

        finally:
            logger.debug("Cleaning up...")
            self._cleanup()
            logger.debug("Exiting queue: clean")
            return

    def _cleanup(self):
        logger.debug("Cleaning up")
        incomplete_rows = self.db.select_all_queued_incomplete()
        for i in incomplete_rows:
            logger.debug(f"Setting incomplete: guid: {i['guid']}: row: {i}")
            self.db.mark_unqueued_incomplete(i['guid'])


@retry(delay=3, logger=logger)
def run_file_syncer():
    logger.debug(f"db exists?: {os.path.exists(db.db_path)} | {db.db_path}")
    q = TransferQueue(db)

    logger.debug("Starting queue")
    q.run()
    logger.info("Transfer queue stopped")
