"""Appliance classes for multi_engine_query"""
from __future__ import print_function

# Native modules
from abc import ABCMeta, abstractmethod
import base64
import datetime
import hashlib
import inspect
import io
import json
import logging
import re
import subprocess
import time
import urllib

# 3rd-party modules
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from bs4 import BeautifulSoup

# Application specific modules
from timer import timer
from base_classes import DebugableObject

# Create the logger
logger = logging.getLogger('logger')

class Appliance(DebugableObject):
    """A server configured as a Nexthink Appliance.
    This is an Abstract Base Class to be used to define the various types of
    Appliances that exist in the Nexthink Platform: Portal, Engine, etc.
    All Appliances have the following Properties:

    Attributes:
        hostname_fqdn: The Appliances hostname as an fqdn.
        name: The logical name.
        port: The port to target API calls to
        credentials: Base64 encoded credentials to use in API calls
    """

    __metaclass__ = ABCMeta

    def __init__(self, hostname_fqdn, name, port, credentials):
        self._hostname_fqdn = hostname_fqdn
        self._name = name
        self._port = port
        self._credentials = credentials
        self._create_session()

    @property
    def hostname_fqdn(self):
        return self._hostname_fqdn
    
    @property
    def name(self):
        return self._name
    
    @property
    def port(self):
        return self._port
    
    def get_default_headers(self):
        return {
            'Authorization': 'Basic ' + self._credentials,
            'Accept': 'application/json'}

    def _create_session(self):
        """Create reqeusts session object for making API calls to the Appliance
        """
        self._session = requests.Session()
        self._session.headers.update(self.get_default_headers())

    def _format_api(self, api):
        """ Formats the API string by adding the protocol, 
            and converte spaces and hash marks """
        fapi = None
        if api.lower().startswith('https://'):
            fapi = api
        else:
            fapi = "https://" + self._hostname_fqdn + ':' + self._port + \
                (api if api[0] == '/' else '/' + api)
        # Convert mutliple spaces to a single space, remove embedded cr and lf
        fapi = ' '.join(fapi.split())
        fapi = fapi.replace(' ','%20').replace('#','%23')
        return fapi

    @abstractmethod
    def appliance_type(self):
        """Retursn a string representing the type of Appliance this is."""
        pass

    def _process_html(self, htmldoc, table_to_return):
        """ Converts HTML with embedded table of data to a list of dict
            entries representing each row of the table.
            If the specified table contains column headers, those are used to
            construct the field names of the returned dict objects.

            htmldoc = The HTML document to parse
            table_to_return = The nth instance of a <table> tag from the root
                of the <body> tag of the htmldoc.

            Returns = list of zero or more dict objects
        """
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        # Parse the HTML
        soup = BeautifulSoup(htmldoc, "html.parser")
        # Extract the table
        table = soup.find('body').find_all('table', recursive=False)[table_to_return]
        # If you really need to see the returned raw HTML table, uncomment the next line
        # if self.get_debug_mode(): logger.debug('{} - table: {}'.format(func_name, table))
        trs = table.find_all('tr')
        # Process the theader
        headerow = [td.get_text(strip=True) for td in trs[0].find_all('th')] # header row
        if headerow: # if there is a header row, remove it from the list of rows to process
            trs = trs[1:]
        results = []
        # convert every table row
        for tr in trs: 
            tds = tr.find_all('td')
            if len(tds) > 0:
                row = {}
                col = 0
                for td in tr.find_all('td'):
                    colname = headerow[col] if headerow else 'col{}'.format(col)
                    if td.a is not None:
                        row[colname+'.href'] = td.a['href']
                        row[colname+'.text'] = td.a.string
                    else:
                        row[colname+'.text'] = td.string
                    col += 1
                results.append(row) # data row
                if self.get_debug_mode(): logger.debug('{} - row: {}'.format(func_name, row))
        return results

    def execute_html_api(self, api, table_to_return=0):
        """ Executes the specified API against the Appliance and retuns the
            resulting HTML as list of dict objects 

            api = The api after the fqdn of the Appliance to execute
            table_to_return = which instance of the table tag to use as the response
            """
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        results = []
        api = self._format_api(api)
        if self.debug_mode():
            start_time = time.time()
            logger.debug("{} - api: {}".format(func_name, api))
        # Execute the API
        try:
            api_response = self._session.get(api, stream=False, verify=False)
            if self.debug_mode(): logger.debug('{} - api_response.status_code: {}'.format(func_name, api_response.status_code))
        except requests.exceptions.ConnectionError as e:
            logger.error("{} - Unable to get results from Nexthink. {}".format(func_name, e))
            return None
        # Process and parse the response
        results = []
        if api_response.ok:
            api_html = api_response.text
            results = self._process_html(api_html, table_to_return)
        if self.debug_mode():
            end_time = time.time()
            logger.debug("{} - retrieved {} objects in {}".format(func_name, len(results), timer(start_time, end_time)))
        return results

    def execute_json_api(self, api):
        """ Executes the specified API against the Appliance and retusns the
            resulting json objecs as a list of dict objects 

            api = The api after the fqdn of the Appliance to execute
            """
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        results = []
        api = self._format_api(api)
        if self.debug_mode():
            start_time = time.time()
            logger.debug("{} - api: {}".format(func_name, api))
        # Execute the API
        try:
            api_response = self._session.get(api, stream=False, verify=False)
            if self.debug_mode(): logger.debug('{} - api_response.status_code: {}'.format(func_name, api_response.status_code))
        except requests.exceptions.ConnectionError as e:
            logger.error("{} - Unable to get results from Nexthink. {}".format(func_name, e))
            return None
        # Process and parse the response
        results = []
        if api_response.ok:
            results = api_response.json()
        if self.debug_mode():
            end_time = time.time()
            logger.debug("{} - Retrieved {} objects in {}".format(func_name, len(results), timer(start_time, end_time)))
        return results

    def post_json_api(self, api, body):
        """ Posts the specified API against the Appliance and returns the
            resulting json objecs as a list of dict objects 

            api: The api after the fqdn of the Appliance to execute
            body: dict object containing the paylod to post
            """
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        results = []
        api = self._format_api(api)
        if self.debug_mode():
            start_time = time.time()
            logger.debug("{} - api: {}".format(func_name, api))
        # Post the API
        try:
            headers = self.get_default_headers()
            headers['content-type'] = 'application/json'
            api_response = self._session.post(api, json=body, headers=headers, stream=False, verify=False)
            if self.debug_mode(): logger.debug('{} - api_response.status_code: {}'.format(func_name, api_response.status_code))
        except requests.exceptions.ConnectionError as e:
            logger.error("{} - Unable to POST results to Nexthink. {}".format(func_name, e))
            return None
        # Process and parse the response
        results = []
        if api_response.ok:
            if api_response.text[1:] == '{':
                results = json.loads(api_response.text)
            else:
                # Create faux json response
                results.append({"text":api_response.text})
        if self.debug_mode():
            end_time = time.time()
            logger.debug("{} - Retrieved {} objects in {}".format(func_name, len(results), timer(start_time, end_time)))
        return results

class PortalAppliance(Appliance):
    """A Portal Appliance
    Portal Appliances have the following Properties:

    Attributes:
        hostname_fqdn: The Appliances hostname as an fqdn.
        name: The logical name.
        credentials: Base64 encoded credentials to use in Portal API queries
        list_engines_api: The API for retrieving the list of engines from the Portal
        act_api: The base API for making Remote Action calls from the Portal
    """

    @classmethod
    def create(cls, config):
        return cls(config.portal_server, config.portal_name,
            config.portal_port, config.portal_credentials,
            config.portal_list_engines_api, config.portal_act_api)

    def __init__(self, hostname_fqdn, name, port, credentials,
                 list_engines_api, act_api):
        """Returns an initialized Portal Appliance object."""
        super(PortalAppliance, self).__init__(hostname_fqdn, name, port, credentials)
        self._list_engines_api = list_engines_api
        self._act_api = act_api
 
    def __repr__(self):
        return ('PortalAppliance(hostname_fqdn={!r}, name={!r}, port={!r}, '
                'credentials=None, list_engines_api = {!r}, act_api={!r})'.format(
            self._hostname_fqdn, self._name, self._port, self._list_engines_api, self._act_api))

    def appliance_type(self):
        """Retursn a string representing the type of Appliance this is."""
        return "Portal"

    def execute_remote_action(self, remote_action_id, device_list):
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        results = []
        if self.debug_mode():
            start_time = time.time()
            logger.debug("{} - remote_action_id: {}, device_list count: {}".format(func_name, remote_action_id, len(device_list)))
        # Construct payload
        payload = {
            "RemoteActionUid": remote_action_id,
            "DeviceUids": [d.device_uid for d in device_list]
        }
        if self.debug_mode(): logger.debug('{} - Payload before calling RA: {}'.format(func_name, payload))
        response = self.post_json_api(self._act_api, payload)
        if len(response) == 0: response = None
        if self.debug_mode():
            end_time = time.time()
            logger.debug("{} - Executed Remote Action on {} objects in {}. Response:  {}".format(func_name, len(device_list), timer(start_time, end_time), response))
        return response

    def get_engine_list(self, engine_port=1671, only_connected=False):
        """Retursn a list of EngineAppliance instances from this Portal."""
        func_name = self.__class__.__name__ + '.' + inspect.currentframe().f_code.co_name
        results = []
        if self.debug_mode():
            start_time = time.time()
            logger.debug('{} - Start.'.format(func_name))
        response = self.execute_json_api(self._list_engines_api)
        # Create an EngineAppliance instance for each result
        for resp in response:
            if self.debug_mode(): logger.debug('{0} - Processing resp: {1!r}'.format(func_name, resp))
            # If only_active, make sure the engine is active before creating
            if ((not only_connected) or (only_connected and (resp['status'] == 'CONNECTED'))):
                eng = EngineAppliance(resp['address'], resp['name'], engine_port, self._credentials)
                results.append(eng)
            else:
                if self.debug_mode(): logger.debug('{} - Skipping disconnected Engine: {}'.format(func_name, resp['name']))
        if self.debug_mode():
            end_time = time.time()
            logger.debug('{} - Execute of List Engines API returned {} objects in {}. Results: {}'.format(func_name, len(results), timer(start_time, end_time), results))
        return results
    
class EngineAppliance(Appliance):
    """An Engine Appliance
    Engine Appliances have the following Properties:

    Attributes:
        hostname_fqdn: The Appliances hostname as an fqdn.
        name: The logical name.
        port: The port to target API calls to
        credentials: Base64 encoded credentials to use in API calls
    """

    @classmethod
    def create(cls, source_object):
        return cls(source_object.address, source_object.name,
            source_object.port, source_object.credentials)

    def __init__(self, hostname_fqdn, name, port, credentials):
        """Returns an initialized Engine Appliance object."""
        super(EngineAppliance, self).__init__(hostname_fqdn, name, port, credentials)
    
    def __repr__(self):
        return 'EngineAppliance(hostname_fqdn={!r}, name={!r}, credentials=None, port={!r})'.format(
            self._hostname_fqdn, self._name, self._port)

    def appliance_type(self):
        """Retursn a string representing the type of Appliance this is."""
        return "Engine"
