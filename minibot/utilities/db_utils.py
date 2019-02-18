#!/usr/bin/python -u
# encoding: utf-8
import os.path
import sqlite3 as sql


# database info
_db_path = './utilities/remote_movies.db'
_schema_path = './utilities/schema.sql'
_table_name = 'remote_movies'


class FileTransferDB(object):
    def __init__(self, db_path=_db_path, table_name=_table_name):
        self.db_path = os.path.abspath(os.path.expanduser(db_path))
        self.table_name = table_name
        self._schema_path = _schema_path
        self._create_from_schema()

    def _create_from_schema(self):
        connection = sql.connect(self.db_path)
        cur = connection.cursor()
        with open(self._schema_path) as schema:
            cur.executescript(schema.read())

    def insert(self, guid, remote_path):
        with sql.connect(self.db_path) as con:
            add_movie_sql = 'INSERT INTO {} (guid, remote_path) VALUES (?, ?)'.format(
                self.table_name)
            cur = con.cursor()
            cur.execute(add_movie_sql, (guid, remote_path))
            con.commit()

    def _select_movie(self, query):
        query_sql = 'SELECT * FROM {} WHERE {}'.format(
            self.table_name, query)
        with sql.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(query_sql)

            return cur

    def select_guid(self, guid):
        guid_query = 'SELECT * FROM {} WHERE guid=?'.format(
            self.table_name)
        with sql.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(guid_query, (guid,))
            result = cur.fetchone()

        return result

    def select_all_movies(self):
        query_sql = 'SELECT * FROM {}'.format(self.table_name)
        with sql.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(query_sql)
            rows = cur.fetchall()

        return rows

    def select_all_unqueued_movies(self):
        unqueued_query = 'queued = 0 AND complete = 0'
        cur = self._select_movie(unqueued_query)
        rows = cur.fetchall()

        return rows

    def select_one_incomplete(self):
        incomplete_query = 'queued = 1 AND complete = 0'
        cur = self._select_movie(incomplete_query)
        result = cur.fetchone()

        return result

    def _update_status(self, guid, column, val):
        update_sql = 'UPDATE {} SET {} = {} WHERE guid=?'.format(
                    self.table_name, column, val)
        with sql.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(update_sql, (guid,))
            con.commit()

    def mark_queued(self, guid):
        self._update_status(guid, 'queued', 1)
        self._update_status(guid, 'complete', 0)

    def mark_complete(self, guid):
        self._update_status(guid, 'queued', 0)
        self._update_status(guid, 'complete', 1)

    def mark_unqueued_incomplete(self, guid):
        self._update_status(guid, 'queued', 0)
        self._update_status(guid, 'complete', 0)

    @staticmethod
    def row_to_dict(row):
        row_id, guid, remote_path, queued, complete = row
        item_dict = {
            'id': row_id,
            'guid': guid,
            'remote_path': remote_path,
            'queued': queued,
            'complete': complete
        }

        return item_dict
