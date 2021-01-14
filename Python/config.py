"""Configuration settings for console app
"""

# Native modules
import configparser
from configparser import ExtendedInterpolation
import datetime
import glob
import logging
from logging.handlers import RotatingFileHandler
import os
import socket
import sys

# Create the logger
logger = logging.getLogger('logger')

class NXQLQuery(object):
    """A class representing an NXQL Query to execute
    
    Attributes:
        section - The name of the section from the NXQL config file
        query - The actual NXQL query
        output_path - The primary folder to use to store the generated output file
        sub_folder - An optional sub-folder within output_path to stor the generated output file
        filename - The pattern to use to generate the file name (may include {query} and {rundate})
        delimiter - The delimiter to use between fields
        platforms - The platform qualifiers
    """
    
    @classmethod
    def create(cls, primary_config, nxql_config, section_name):
        # Make sure the query configuraiton contains the required keywords
        if 'query' not in nxql_config[section_name]:
            msg = 'ERROR: Configuration file for query "{0}" ("{1}") is missing the required "query" keyword.'.format(
                section_name, primary_config.query_file)
            logger.error('NXQLQuery.create - {}'.format(msg))
            print(msg)
            return None
        else:
            query = nxql_config.get(section_name, 'query')
        
        # Setup initial values
        output_path = primary_config.query_output_path
        sub_folder = None
        filename = primary_config.query_output_filename
        delimiter = primary_config.query_delimiter
        platforms = primary_config.query_platforms

        # Look for any configuration-file specific overrides
        if 'Overrides' in nxql_config.sections():
            if 'query_output_path' in nxql_config['Overrides']:
                output_path = nxql_config.get('Overrides', 'query_output_path')
            if 'query_sub_folder' in nxql_config['Overrides']:
                sub_folder = nxql_config.get('Overrides', 'query_sub_folder')
            if 'filename' in nxql_config['Overrides']:
                filename = nxql_config.get('Overrides', 'filename', raw=True)
            if 'delimiter' in nxql_config['Overrides']:
                delimiter = nxql_config.get('Overrides', 'delimiter', raw=True)
            if 'platforms' in nxql_config['Overrides']:
                platforms = nxql_config.get('Overrides', 'platforms', raw=True)

        # Look for any query/section specific overrides
        if 'query_output_path' in nxql_config[section_name]:
            output_path = nxql_config.get(section_name, 'query_output_path')
        if 'query_sub_folder' in nxql_config[section_name]:
            sub_folder = nxql_config.get(section_name, 'query_sub_folder')
        if 'filename' in nxql_config[section_name]:
           filename = nxql_config.get(section_name, 'filename', raw=True)
        if 'delimiter' in nxql_config[section_name]:
            delimiter = nxql_config.get(section_name, 'delimiter', raw=True)
        if 'platforms' in nxql_config[section_name]:
            platforms = nxql_config.get(section_name, 'platforms', raw=True)

        # Create and return the object
        return cls(
            section_name, query, output_path, sub_folder, filename, delimiter,
            platforms)

    def __init__(self, name, query, output_path, sub_folder, filename, delimiter, platforms):
        self._name = name
        self._query = query
        self._output_path = output_path
        self._sub_folder = sub_folder
        self._filename = filename
        self._delimiter = delimiter
        self._platforms = platforms

    def __str__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __repr__(self):
        return ('NXQLQuery(name={!r}, query={!r}, output_path={!r}, '
                'sub_folder={!r}, filename={!r}, delimiter={!r}, '
                'platforms={!r})'.format(
            self._name, self._query, self._output_path, self._sub_folder, 
            self._filename, self._delimiter, self._platforms))

    def get(self, property):
        return self.__getattribute__("_"+property)

    @property
    def name(self):
        return self._name
    
    @property
    def query(self):
        return self._query
    
    @property
    def output_path(self):
        return self._output_path
        
    @property
    def sub_folder(self):
        return self._sub_folder
        
    @property
    def filename(self):
        return self._filename
    
    @property
    def delimiter(self):
        return self._delimiter
    
    @property
    def platforms(self):
        return self._platforms.split(',')


class MultiEngineQueryConfig(object):

    def _configure_args(self, args):
        """ Set log to debug if argument passed """
        # Set based on the presence of the -d flag and the e option
        self._debug_engine = True if args.options['engine'] else False
        # Set based on the presence of the -d flag and the g option
        self._debug_general = True if args.options['general'] else False
        # Set based on the presence of the -d flag and the p option
        self._debug_portal = True if args.options['portal'] else False
        self._debug = self._debug_engine or self._debug_general or \
            self._debug_portal
        # Set based on the presence of the -i flag on the command line
        # Debug implies verbose info too
        self._info = True if args.info else self._debug
        # Check for and process exclude (-x) flag
        # Set based on the presence of the -x flag and the f option
        self._exclude_device = True if args.exclude['file'] else False
        # Get the type of name being supplied: s)single, or g)group
        self._query_is_group = True if args.query_type == 'g' else False
        # Capture the query group or section name
        self._query_name = args.name

    def _load_config(self):
        # Get the environment infor (base name, path,etc.)
        self._app_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self._full_hostname = socket.gethostname().lower()
        self._hostname = self._full_hostname.split('.')[0]
        path = os.path.dirname(os.path.abspath(__file__)) # Script execution path
        # Set execution location to the current script's location
        os.chdir(path)
        # Pull in the configuration file
        self._conf = configparser.ConfigParser(allow_no_value=True)
        self._conf.read("." + self._app_name + ".conf")
        # Make sure all required sections are present
        __required_sections = ['General', 'Logging', 'Email', 'Portal', 'Engine']
        sections = self._conf.sections()
        missing_sections = []
        for section in __required_sections:
            if section not in sections:
                missing_sections.append(section)
        if len(missing_sections) >= 1:
            print('ERROR: Configuration file is missing the following required sections: {0}'.format(
                ','.join(missing_sections)))
            exit(1)

    def _configure_logger(self):
        # Retrieve the environment string
        self._env = self._conf.get('General', 'environment')
        # Get Logging configuration information
        self._rundate = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        log_name = '{}.{}.{}.{}.{}.log'.format(
            self._query_name, self._conf.get('Logging', 'log_basename'), 
            self.env, self.full_hostname, self._rundate) # Location to write the log files
        self._log_path = os.path.join(self._conf.get('Logging', 'log_path'), log_name)
        print('Log file: {0}'.format(self._log_path))
        log_max_bytes = self._conf.getint('Logging', 'log_max_bytes') # Max size of a single log file
        log_backup_count = self._conf.getint('Logging', 'log_max_bytes') # Max number of log files before the files rollover
        # Create the logger (Used by 'helpers' module too)
        logger = logging.getLogger('logger')
        handler = RotatingFileHandler(self._log_path, maxBytes=log_max_bytes, backupCount=log_backup_count)
        formatter = logging.Formatter('%(asctime)s - %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if self._debug:
            logger.setLevel(logging.DEBUG)
            if self.verbose: print('Setting log level to DEBUG')
        else:
            logger.setLevel(logging.INFO)
            if self.verbose: print('Setting log level to INFO')

    def _load_items(self):
        """ Load the items from the configuration file """
        # For sending emails via SMTP
        self._email_results = (self._conf.getint('Email', 'email_results') == 1)
        self._email_server = self._conf.get('Email', 'email_server', raw=True)
        self._email_port = self._conf.getint('Email', 'email_port')
        self._email_timeout = self._conf.getint('Email', 'email_timeout')
        self._email_from = self._conf.get('Email', 'email_from', raw=True)
        self._email_recipients = self._conf.get('Email', 'email_recipients', raw=True)
        self._email_subject = self._conf.get('Email', 'email_subject', raw=True)
        self._email_include_log = (self._conf.getint('Email', 'email_include_log') == 1)
        self._email_zip_log = (self._conf.getint('Email', 'email_zip_log') == 1)
        self._email_remove_zip_log = (self._conf.getint('Email', 'email_remove_zip_log') == 1)
        self._email_include_unsuccessful = (self._conf.getint('Email', 'email_include_unsuccessful') == 1)
        self._email_include_deferred = (self._conf.getint('Email', 'email_include_deferred') == 1)
        self._email_body = []
        # Portal related
        self._portal_server = self._conf.get('Portal', 'portal_server')
        self._portal_name = self._conf.get('Portal', 'portal_name')
        self._portal_port = self._conf.get('Portal', 'portal_port')
        self._portal_credentials = self._conf.get('Portal', 'portal_credentials', raw=True)
        self._portal_list_engines_api = self._conf.get('Portal', 'portal_list_engines_api')
        self._portal_remote_action_api = self._conf.get('Portal', 'portal_remote_action_api')
        # Engine related
        self._engine_port = self._conf.get('Engine', 'engine_port')
        self._engine_credentials = self._conf.get('Engine', 'engine_credentials')
        # Query location items
        self._query_path = self._conf.get('Queries', 'query_path', raw=True)
        self._query_pattern = self._conf.get('Queries', 'query_pattern', raw=True)
        # The default output path for the queries.
        # May be overridden in the individual query file.
        self._query_output_path = self._conf.get('Queries', 'query_output_path')
        # The default output filename pattern.
        # May be overridden in the individual query file.
        self._query_output_filename = self._conf.get('Queries', 'filename', raw=True)
        # The default output field delimiter.
        # May be overridden in the individual query file.
        self._query_delimiter = self._conf.get('Queries', 'delimiter', raw=True)
        # The default platform specifier.
        # May be overridden in the individual query file.
        self._query_platforms = self._conf.get('Queries', 'platforms', raw=True)

    def _load_queries(self):
        # Get the list of qury files
        query_path = os.path.join(self._query_path,self._query_pattern)
        query_files = glob.glob(query_path)
        if len(query_files) == 0:
            print('ERROR: No Query configuration files were found in "{0}".'.format(query_path))
            exit(1)
        # Find the first query file that contains the requesteed group name or section
        query_conf = None
        found = False
        for qf in query_files:
            logger.debug('Looking for NXQL Query (Group or Single) "{0}".  Reading file: "{1}".'.format(self._query_name, qf))
            query_conf = configparser.ConfigParser(
                interpolation=ExtendedInterpolation(), allow_no_value=True)
            query_conf.read(qf)
            if self._query_is_group:
                if query_conf.has_section('General') and \
                   query_conf.has_option('General', 'group_name') and \
                   self._query_name == query_conf.get('General', 'group_name'):
                    self._qf = qf
                    found = True
                    break
            else:
                if query_conf.has_section(self._query_name):
                    self._qf = qf
                    found = True
                    break
        # Generate an error if not found
        if not found:
            msg = 'ERROR: A configuration file containing the specified Query Group, or Named Query ("{0}") was not found in "{1}".'.format(
                self._query_name, query_path)
            logger.error('_load_queries - {}'.format(msg))
            print(msg)
            exit(2)
        # If a Query Group, generate an array of one or more queries based on the contents of the file.
        self._queries = []
        if self._query_is_group:
            for section in query_conf.sections():
                if section not in ['General', 'Overrides']:
                    query = NXQLQuery.create(self, query_conf, section)
                    if query:
                        self._queries.append(query)
        # Otherwise, just a single named query so generate an array of one
        else:
            query = NXQLQuery.create(self, query_conf, self._query_name)
            if query:
                self._queries.append(query)
        # If no valid queries were able to be created, than exit
        if len(self._queries) == 0:
            msg = 'ERROR: No valid queries were able to be found for the specified Query Group, or Named Query ("{0}") in "{1}".'.format(
                self._query_name, self._qf)
            logger.error('_load_queries - {}'.format(msg))
            print(msg)
            exit(3)
    
    def __init__(self, args):
        self._configure_args(args)
        self._load_config()
        self._configure_logger()
        self._load_items()
        self._load_queries()
        logger.debug('config: {}'.format(self))

    def __str__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def get(self, property):
        return self.__getattribute__("_"+property)

    @property
    def rundate(self):
        return self._rundate

    @property
    def log_path(self):
        return self._log_path

    @property
    def verbose(self):
        return self._info

    @property
    def debug(self):
        return self._debug

    @property
    def debug_engine(self):
        return self._debug_engine

    @property
    def debug_general(self):
        return self._debug_general

    @property
    def debug_portal(self):
        return self._debug_portal

    @property
    def exclude_file(self):
        return self._exclude_file

    @property
    def env(self):
        return self._env

    @property
    def full_hostname(self):
        return self._full_hostname

    @property
    def email_results(self):
        return self._email_results

    @property
    def email_server(self):
        return self._email_server

    @property
    def email_port(self):
        return self._email_port

    @property
    def email_timeout(self):
        return self._email_timeout

    @property
    def email_from(self):
        return self._email_from

    @property
    def email_recipients(self):
        return self._email_recipients

    @property
    def email_subject(self):
        return self._email_subject

    @property
    def email_include_log(self):
        return self._email_include_log
    
    @property
    def email_zip_log(self):
        return self._email_zip_log
    
    @property
    def email_remove_zip_log(self):
        return self._email_remove_zip_log
    
    @property
    def email_include_unsuccessful(self):
        return self._email_include_unsuccessful

    @property
    def email_include_deferred(self):
        return self._email_include_deferred

    @property
    def email_body(self):
        return self._email_body

    def add_to_email(self, row):
        """Appends 'row' to the email body list"""
        self._email_body.append(row)

    @property
    def portal_server(self):
        return self._portal_server
        
    @property
    def portal_name(self):
        return self._portal_name
        
    @property
    def portal_port(self):
        return self._portal_port
        
    @property
    def portal_credentials(self):
        """ Base-64 encoded username:password for Basic Auth """
        return self._portal_credentials
    
    @property
    def portal_act_api(self):
        return self._portal_remote_action_api
        
    @property
    def portal_list_engines_api(self):
        return self._portal_list_engines_api

    @property
    def engine_port(self):
        return self._engine_port

    @property
    def engine_credentials(self):
        """ Base-64 encoded username:password for Basic Auth """
        return self._engine_credentials
    
    @property
    def query_is_group(self):
        return self._query_is_group
    
    @property
    def query_name(self):
        return self._query_name
 
    @property
    def query_file(self):
        return self._qf
        
    @property
    def queries(self):
        return self._queries

    @property
    def query_output_path(self):
        return self._query_output_path

    @property
    def query_output_filename(self):
        return self._query_output_filename
    
    @property
    def query_delimiter(self):
        return self._query_delimiter
    
    @property
    def query_platforms(self):
        return self._query_platforms

