#!/usr/bin/python -u
# encoding: utf-8
from __future__ import print_function, unicode_literals, absolute_import
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

    def guid_search(self, imdb_guid):
        """Queries OMDb (omdbapi.com) for movie information using a provided
        IMDb guid and returns the response code and json response text.

        Requires: imdb_guid(str) - IMDb guid to search for

        Returns:
            response.status_code,
            json.loads(response.text)
        """

        if self.debug:
            print('Searching OMDb for guid: {}'.format(imdb_guid))

        query = '?i={guid}&{plot_token}={plot_detail}'.format(
            guid=imdb_guid, plot_token=constants.PLOT_TOKEN,
            plot_detail=self._plot_detail)

        return self._query_omdb(query)

    def title_search(self, title, year=None):
        """Queries OMDb (omdbapi.com) for movie information using
        a title and optionally, a year and returns the response code
        and json response text.

        Requires: title(str) - movie title

        Optional:
          year(str)  - year movie was released (optional)
          plot(str)  - short | long. Choose the amount of plot detail
            to request (optional)

        Returns:
            response.status_code,
            json.loads(response.text)

        """
        query = '?{title_token}={title}'.format(
            title_token=constants.TITLE_TOKEN, title=title)
        if year:
            query = query + '&{year_token}={year}'.format(
                year_token=constants.YEAR_TOKEN, year=year)

        query = query + '&{plot_token}={plot_detail}'.format(
            plot_token=constants.PLOT_TOKEN, plot_detail=self._plot_detail)

        if self.debug:
            print('Searching OMDb for title: {} {}'.format(title, year))

        return self._query_omdb(query)

    def _query_omdb(self, query):
        _omdb_query_url = '{url}/{query}&{api}={apikey}'.format(
            url=constants.OMDB_URL, query=query,
            api=constants.API_TOKEN, apikey=self.api_key)

        if self.debug:
            print('Query url: {}'.format(_omdb_query_url))

        response = requests.get(
            _omdb_query_url,
            headers={'Content-Type': 'application/json'}
        )

        return response.status_code, json.loads(response.text)
