#!/usr/bin/env python3
import json

import requests

from utilities import constants


class OMDb(object):
    def __init__(self, api_key=None, short_plot=True, debug=False):
        self.api_key = api_key
        self.debug = debug
        self.short_plot = short_plot

    @property
    def _plot_detail(self):
        if self.short_plot:
            return constants.PLOT_SHORT
        else:
            return constants.PLOT_LONG

    def search(self, imdb_guid=None, title=None, year=None):
        if self.debug:
            print("Searching OMDb... guid: [{}] title: [{}] year: [{}]".format(
                imdb_guid, title, year))

        query_dict = {
            constants.GUID_TOKEN: imdb_guid,
            constants.TITLE_TOKEN: title,
            constants.YEAR_TOKEN: year,
            constants.PLOT_TOKEN: self._plot_detail,
            constants.API_TOKEN: self.api_key,
        }

        if self.debug:
            print(f"url: {constants.OMDB_URL}")
            print(f"query: {query_dict}")

        response = requests.get(
            constants.OMDB_URL, params=query_dict,
            headers={"Content-Type": "application/json"}
        )

        return json.loads(response.text, encoding="unicode"), response.status_code
