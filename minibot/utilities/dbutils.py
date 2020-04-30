#!/usr/bin/env python3
import os.path
import sqlite3 as sql

# database info
_db_filename = "remote_movies.db"
_schema_filename = "schema.sql"
_db_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), _db_filename))
_schema_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), _schema_filename))

_table_name = "remote_movies"
_guid_col = "guid"
_remote_path_col = "remote_path"
_queued_col = "queued"
_complete_col = "complete"

_update_queued_col_statement = "UPDATE remote_movies SET queued=? WHERE guid=?"
_update_complete_col_statement = "UPDATE remote_movies SET complete=? WHERE guid=?"
_remove_guid_statement = "DELETE FROM remote_movies WHERE guid=?"


class FileTransferDB(object):
    def __init__(self,
                 db_path=_db_path,
                 schema_path=_schema_path,
                 table_name=_table_name):
        self.db_path = db_path
        self.schema_path = schema_path
        self.table_name = table_name
        self._create_from_schema()

        self.guid_col = _guid_col
        self.rempath_col = _remote_path_col
        self.qd_col = _queued_col
        self.complete_col = _complete_col

    def _create_from_schema(self):
        connection = sql.connect(self.db_path)
        connection.row_factory = sql.Row
        cur = connection.cursor()
        with open(self.schema_path) as schema:
            cur.executescript(schema.read())

    def insert(self, guid, remote_path):
        statement = f"INSERT INTO remote_movies " \
                    f"(guid, remote_path) VALUES (?, ?)"
        params = (guid, remote_path)
        with sql.connect(self.db_path) as con:
            con.row_factory = sql.Row
            con.text_factory = lambda x: str(x, "utf-8", "ignore")
            cur = con.cursor()
            cur.execute(statement, params)
            con.commit()

    def _select_movie(self, query):
        query_sql = f"SELECT * FROM remote_movies WHERE {query}"
        with sql.connect(self.db_path) as con:
            con.row_factory = sql.Row
            con.text_factory = lambda x: str(x, "utf-8", "ignore")
            cur = con.cursor()
            cur.execute(query_sql)

            return cur

    def select_guid(self, guid):
        statement = f"SELECT * FROM remote_movies WHERE guid=?"
        params = (guid,)
        with sql.connect(self.db_path) as con:
            con.row_factory = sql.Row
            con.text_factory = lambda x: str(x, "utf-8", "ignore")
            cur = con.cursor()
            cur.execute(statement, params)
            result = cur.fetchone()

        return result

    def select_all_movies(self):
        query_sql = "SELECT * FROM remote_movies"
        with sql.connect(self.db_path) as con:
            con.row_factory = sql.Row
            con.text_factory = lambda x: str(x, "utf-8", "ignore")
            cur = con.cursor()
            cur.execute(query_sql)
            rows = cur.fetchall()

        return rows

    def select_all_unqueued_movies(self):
        unqueued_query = "queued = 0 AND complete = 0"
        cur = self._select_movie(unqueued_query)
        rows = cur.fetchall()

        return rows

    def select_all_queued_incomplete(self):
        incomplete_query = "queued = 1 AND complete = 0"
        cur = self._select_movie(incomplete_query)
        rows = cur.fetchall()

        return rows

    def select_one_incomplete(self):
        incomplete_query = "queued = 1 AND complete = 0"
        cur = self._select_movie(incomplete_query)
        result = cur.fetchone()

        return result

    def _execute_sql(self, statement, params):
        with sql.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(statement, params)
            con.commit()

    def mark_queued(self, guid):
        self._execute_sql(_update_queued_col_statement, (1, guid,))
        self._execute_sql(_update_complete_col_statement, (0, guid,))

    def mark_complete(self, guid):
        self._execute_sql(_update_queued_col_statement, (0, guid,))
        self._execute_sql(_update_complete_col_statement, (1, guid,))

    def mark_unqueued_incomplete(self, guid):
        self._execute_sql(_update_queued_col_statement, (0, guid,))
        self._execute_sql(_update_complete_col_statement, (0, guid,))

    def remove_guid(self, guid):
        self._execute_sql(_remove_guid_statement, (guid,))
