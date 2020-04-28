"""helper functions for multi_engine_query"""

# Native moduels
import csv
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import inspect
import logging
import os
from os.path import basename
import smtplib
import time
import zipfile

# Applicaiton specific modules
import config
from timer import timer
from appliance_classes import PortalAppliance, EngineAppliance

def init(config):
    """ Create the logger, and enable Class-level debugging 

    Arguments:
        config: Initialized MultiEngineQueryConfig instance
    returns:
        logger instance
    """
    logger = logging.getLogger('logger')
    EngineAppliance.set_debug_mode(config.debug_engine)
    PortalAppliance.set_debug_mode(config.debug_portal)
    return logger

def create_output_file(logger, config, query):
    """ Create the output file based on the specified configuration 

    Arguments:
        logger: Initialized logger instance
        config: Initialized MultiEngineQueryConfig instance
        query: Initialized NXQLQuery instance
    Returns:
        string: output file name
        bool: True if successful
    """
    func_name = inspect.currentframe().f_code.co_name

    # Construct the path name.  If it does not exists, create it.
    fpath = os.path.join(query.output_path, query.sub_folder) if query.sub_folder else query.output_path
    if not os.path.exists(fpath):
        os.makedirs(fpath)
        if config.verbose:
            logger.info('{0} - Created output folder: "{1}".'.format(func_name, fpath))

    # Construct the output filename (including path)
    fname = os.path.join(fpath,
        query.filename.format(
            query=query.name,
            rundate=config.rundate))

    # Attempt to create the file
    try:
        f = open(fname, "w")
        f.close()
    except IOError as e:
        logger.error('{0} - I/O error({1}): {2}'.format(func_name, e.errno, e.strerror))
        return fname, False
    except:  # handle other exceptions such as attribute errors
        logger.error('{0} - Unexpected error: {1}'.format(func_name, sys.exc_info()[0]))
        return fname, False
    return fname, True

def run_query_on_engine(logger, config, engine, query):
    """ Runs the NXQL for the named query section and returns the results
        as a list of dictionaries

        Arguments:
        logger: Initialized logger instance
        config: Initialized MultiEngineQueryConfig instance
        engine: Initialized Engine instance
        query: Initialized NXQLQuery instance

        Returns:
        list of dict representint results
    """
    func_name = inspect.currentframe().f_code.co_name
    start_time = time.time()
    if config.debug_general:
        logger.debug("{} - Starting".format(func_name))
    # Build the query to get the desired objects
    get_query = ['/2/query?']
    # Add platforms
    for platform in query.platforms:
        get_query.append('platform='+platform+'&')    
    # Add query
    get_query.append('query='+query.query+'&')
    # Bring back objects as dict of json objects
    get_query.append('format=json')
    # Retrieve the requested objects
    engine_objects = engine.execute_json_api(''.join(get_query))
    if config.debug_general: logger.debug('{} - engine.execute_json_api() returned {} Engine objects.\n\t{!r}'.format(func_name, len(engine_objects), engine_objects))
    end_time = time.time()
    if config.verbose:
        logger.info('{} - {} result rows retrived from Engine at {} in {}'.format(func_name, len(engine_objects), engine.hostname_fqdn, timer(start_time, end_time)))
    return engine_objects

def write_to_output_file(logger, config, query, fname, objects, field_names, need_headers):
    """ Create the output file based on the specified configuration 

    Arguments:
        logger: Initialized logger instance
        config: Initialized MultiEngineQueryConfig instance
        query: Initialized NXQLQuery instance
        fname: File name to write to
        objects: list of dict objects to write
        field_name: list of strings to use as field names for the dict
        need_headers: bool if True write headers
    Returns:
        output file name and whether successful or not
    """
    func_name = inspect.currentframe().f_code.co_name
    start_time = time.time()
    success = True
    try:
        with open(fname, 'a', newline='') as write_obj:
            # Create a writer object from csv module
            dict_writer = csv.DictWriter(write_obj, extrasaction='ignore',
                fieldnames=field_names, delimiter=query.delimiter,
                quoting=csv.QUOTE_NONNUMERIC)
            # If the first time, write out the Header wrote
            if need_headers:
                dict_writer.writeheader()
            # Add dictionary to the csv
            dict_writer.writerows(objects)
    except IOError as io_err:
        logger.error('{0} - I/O error({1}): {2}'.format(func_name, io_err.errno, io_err.strerror))
        success = False
    except Exception as exc:  # handle other exceptions such as attribute errors
        logger.error('{0} - Unexpected error: {1!r}'.format(func_name, exc))
        success = False
    end_time = time.time()
    if config.verbose:
        logger.info('{} - Wrote {} result rows in {}'.format(func_name, len(objects), timer(start_time, end_time)))
    return success

def send_mail(logger, config):
    """Send email function

    Function to send a email using the SMTP configuration from the Appliance.
    Works only if no authentication is needed on the SMTP server
    The subject, body of the email message, and server details are in the config object.
    If there are no recipients, than just return.

    Arguments:
        logger: Initialized logger instance
        config: Initialized MultiEngineQueryConfig instance
    """
    func_name = inspect.currentframe().f_code.co_name

    # See if we want emails to be setn
    if not config.email_results:
        logger.debug('{0} - Email with results will not be sent.'.format(func_name))
        return
    logger.debug('{0} - Preparing email to be sent ...'.format(func_name))

    # Parse the recipients to see if we even have any to send the email to
    parsed_recipients = config.email_recipients.split(',')
    if (len(parsed_recipients) == 0):
        logger.warning('{0} - No Email recipeints specified, skipping outbound email.'.format(func_name))
        return
    
    # See if we have an Email Server specified
    elif not config.email_server:
        logger.error('{0} - No SMTP server configured; unable to send email messages'.format(func_name))
    
    else:

        if config.debug: 
            template = '{0} - SMTP server: {1}, Port: {2}, Sending from: {3} To: {4}.'
            message = template.format(func_name, config.email_server, config.email_port, config.email_from, config.email_recipients)
            logger.debug(message)

        # Construct the outbound message header
        msg = MIMEMultipart()
        msg['From'] = config.email_from
        msg['Subject'] = config.email_subject.format(env=config.env, query=config.query_name, rundate=config.rundate)
        msg['To'] = config.email_recipients

        # Construct and attach the email body
        body = msg['Subject'] + ':\r\n'
        body += '\r\n'.join(config.email_body)
        msg.attach(MIMEText(body))

        # Attempt to send the message
        try:
            # Open a connection with the SMTP server
            with smtplib.SMTP(config.email_server, config.email_port, None, config.email_timeout) as smtp:
                # Verify the recipient addresses in advance
                recipients = []
                for recip in parsed_recipients:
                    vresp = smtp.verify(recip)
                    if (vresp[0] == 250):
                        recipients.append(recip)
                    elif (vresp[0] == 252):
                        recipients.append(recip)
                        if config.debug: logger.debug('{0} - Could not verify email address "{1}"; server does not support email address verification, but will still attempt to send to this recipient.'.format(func_name, recip))
                    else:
                        logger.error('{0} - Error while attempting to verify email address "{1}": {2!r}.  Will not attempt to send to this recipient.'.format(func_name, recip, vresp))
                if (len(recipients) == 0):
                    logger.error('Unable to send Email results, no valid recipients.')
                else:
                    # If an attachment is specified, get it and attach it to the message
                    log_path = config.log_path
                    if config.email_include_log:
                        # See if we need to zip first
                        if config.email_zip_log:
                            with zipfile.ZipFile(log_path+'.zip', mode='w', compression=zipfile.ZIP_LZMA) as zf:
                                zf.write(log_path)
                            log_path += '.zip'
                        with open(log_path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=basename(log_path))
                            part['Content-Disposition'] = 'attachment; filename=' + basename(log_path) + ''
                        msg.attach(part)
                    # Attempt to send the email message
                    smtp.sendmail(config.email_from, recipients, msg.as_string())
                    # Remove .zip file if created
                    if config.email_include_log and config.email_zip_log and config.email_remove_zip_log:
                        os.remove(log_path)

        # If an exception occurred, put it's information in the log
        except Exception as ex:
            template = '{0} - An exception of type {1} occurred. Arguments: {2!r}. Exception: {3!r}'
            message = template.format(func_name, type(ex).__name__, ex.args, ex)
            logger.error(message)

        else:
            logger.info('{0} - Email sent successfully to {1}'.format(func_name, config.email_recipients))
