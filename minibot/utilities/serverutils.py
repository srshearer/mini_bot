#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import time
import paramiko
from minibot.utilities import utils
from minibot.utilities import config


def get_file(rem_path, destination=config.IN_PROGRESS_DIR, **kwargs):

    def status(complete, total):
        pct = 100 * complete / total
        c = utils.convert_file_size(complete)
        t = utils.convert_file_size(total)
        progress = '\tprogress: {}% [ {} / {} ]\033[F'.format(pct, c, t)
        sys.stdout.write('\r' + progress)
        time.sleep(1)

    f = os.path.basename(rem_path)

    tmp_dir_path = os.path.expanduser(config.IN_PROGRESS_DIR)
    final_dest_dir_path = os.path.expanduser(destination)

    remote_server = config.REMOTE_FILE_SERVER
    remote_user = config.REMOTE_USER


    print('Copying from remote server: {}@{}:\'{}\''.format(
        remote_user, remote_server, rem_path))
    print('Temp destination: {}'.format(tmp_dir_path))

    local_pub_key = os.path.expanduser(os.path.join("~/.ssh", "id_rsa.pub"))
    ssh = paramiko.SSHClient()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_host_keys(os.path.expanduser(
            os.path.join("~/.ssh", "known_hosts")))
        ssh.connect(
            remote_server, username=remote_user, key_filename=local_pub_key)
        sftp = ssh.open_sftp()

        try:
            download_successful = True

            sftp.get(rem_path, os.path.join(tmp_dir_path, f), callback=status)

            sys.stdout.write('\n')
            msg = 'Transfer successful!'
            print('{}'.format(msg))
        except Exception as e:
            download_successful = False
            final_dest_dir_path = None
            msg = 'Error getting file: {} \n{}'.format(f, e)
            print('{}'.format(msg))
            sftp.close()

            if os.path.exists(os.path.join(tmp_dir_path, f)):
                os.remove(os.path.join(tmp_dir_path, f))

    except Exception as e:
        download_successful = False
        final_dest_dir_path = None
        msg = 'Error connecting to remote host: {}'.format(e)
        print('{}'.format(msg))
        ssh.close()

    final_file_path = None
    if download_successful:
        try:
            final_file_path = os.path.join(final_dest_dir_path, f)
            print('Moving {} to {}'.format(f, final_dest_dir_path))
            os.path.dirname(final_dest_dir_path)
            if not os.path.isdir(final_dest_dir_path):
                os.mkdir(final_dest_dir_path)

            os.rename(os.path.join(tmp_dir_path, f), final_file_path)

        except OSError as e:
            print('Failed to move file \n{}'.format(e))

    return {'path': final_file_path, 'msg': msg}
