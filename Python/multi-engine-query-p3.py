#!/usr/bin/python

# Author: Sorin Gancea, Nexthink Professional Services (sorin.gancea@nexthink.com)
# Last change date: 2020.04.14 (by Jordan Olin, jordan.olin@nexthink.com)
#     Convered to Python 3.6, switched to use requests module instead of urllib
#
# Python version 3.6
#

# Native imports
from datetime import datetime
import inspect
import logging
import os
import time

# Application specific imports
from arg_processor import handle_args
from config import MultiEngineQueryConfig
from timer import timer
from appliance_classes import PortalAppliance, EngineAppliance
from helpers import init, create_output_file, run_query_on_engine, write_to_output_file, send_mail

def finish_process(func_name, logger, config, start_time, finished=True):
    if config.verbose:
        end_time = time.time()
        logger.info("{} - Completed in {}".format(func_name, timer(start_time, end_time)))
    return finished

def run_multi_engine_query(config):
    """ Based on the specified named query, collect all engines, and run the query against
    all engines and put the output in a single .csv file.

    High-level logic:
    1. Create a Portal object instance
    2. Get the list of Engines from the Portal
    3. Create the output file
    For each Engine:
        4. Run the query against that engine
        5. Append the results to the output file

    Arguments:
    config: Initialized MultiEngineQueryConfig object
    """
    func_name = inspect.currentframe().f_code.co_name

    # Create the logger, and enable Class-level debugging
    logger = init(config)

    start_time = time.time()
    if config.verbose:
        logger.info('{} - Starting'.format(func_name))

    # 1. Create a Portal object instance
    portal = PortalAppliance.create(config)

    # 2. Get the list of Connected Engines from the Portal
    portal_start_time = time.time()
    engine_list = portal.get_engine_list(config.engine_port, only_connected=True)
    portal_end_time = time.time()
    msg = 'Retrieved {0} connected Engine{1} from Portal "{2}" in {3}.'.format(
        len(engine_list), 's' if len(engine_list) != 1 else '', portal.name,
        timer(portal_start_time, portal_end_time))
    config.add_to_email(msg)
    print(msg)
    if config.verbose: logger.info("{0} - {1}".format(func_name, msg))
    # If there are no Enigne Appliances, just note the fact and exit.
    if len(engine_list) == 0:
        msg = 'No Engine Appliances are connected or available, so exiting.'
        print(msg)
        config.add_to_email(msg)
        return finish_process(func_name, logger, config, start_time, finished=True)

    # For each query
    for query in config.queries:
        query_start_time = time.time()

        if config.verbose:
            msg = 'Processing Query "{0}".'.format(query.name)
            print(msg)
            config.add_to_email(msg)
            logger.info('{} - {}'.format(func_name, msg))

        # 3. Create the output file
        output_fname, output_created = create_output_file(logger, config, query)
        if not output_created:
            msg = 'Unable to create the output file ("{0}") for Query "{1}", so exiting.'.format(output_fname, query.name)
            print(msg)
            config.add_to_email(msg)
            return finish_process(func_name, logger, config, start_time, finished=True)

        # For each Engine
        first_engine = True
        for engine in engine_list:
            eng_name = '[{0} ({1})]'.format(engine.name, engine.hostname_fqdn)

            # 4. Run the query
            engine_objects = run_query_on_engine(logger, config, engine, query)
            msg = '{0} Retrieved {1} Object{2} to save from this Engine for Query "{3}".'.format(
                eng_name, len(engine_objects), 's' if len(engine_objects) != 1 else '', query.name)
            config.add_to_email(msg)
            print(msg)
            if config.debug_engine:
                logger.debug('{0} - {1}'.format(func_name, msg))

            # 5. Save the query results to the output file
            if len(engine_objects) > 0:
                if first_engine:
                    field_names = engine_objects[0].keys()
                written_ok = write_to_output_file(logger, config, query, output_fname, engine_objects, field_names, first_engine)
                first_engine = False
            elif config.debug_engine:
                logger.debug(
                    '{0} - Skipping write of output file for Engine "{1}", no rows were returned for Query "{2}".'.format(
                        func_name, eng_name, query.name))

        query_end_time = time.time()
        if config.verbose:
            msg = 'Completed collecting and writing results for "{0}" to "{1}" in {2}.'.format(
                query.name, output_fname, timer(query_start_time, query_end_time))
            logger.info('{0} - {1}'.format(func_name, msg))
            print(msg)

    return finish_process(func_name, logger, config, start_time)

def main():

    # Handle command line arguments
    args = handle_args()

    # Initialize the configuration object
    config = MultiEngineQueryConfig(args)

    # Get a logger instance
    logger = logging.getLogger('logger')

    start_time = time.time()
    logger.info('================ Starting Multi-Engine Query script ================')

    # Start the process
    finished = run_multi_engine_query(config)
 
    end_time = time.time()
    total = timer(start_time, end_time)
    logger.info('================ Multi-Engine Query script execution completed in {0} ================'.format(total))

    # Send the email if finished completely, or if no Connected Engine Appliacnes were found..
    # Otherwise we had no active metris to process, so ignore.
    if finished:
        send_mail(logger, config)

if __name__ == '__main__':
    main()
