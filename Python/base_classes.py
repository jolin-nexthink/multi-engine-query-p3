"""Base classes for multi_engine_query"""

# Native modules
from abc import ABCMeta, abstractmethod
import logging

# Create the logger
logger = logging.getLogger('logger')

class DebugableObject(object):
    """A class DebugableObject carries the value of a debug flag.
    All DebugableObjects have the following Properties:

    Attributes:
        None
    """

    __metaclass__ = ABCMeta

    _debug_mode =False

    def __init__(self):
        pass

    @classmethod 
    def get_debug_mode(cls):
        return cls._debug_mode

    @classmethod
    def set_debug_mode(cls, mode):
        cls._debug_mode = mode
        logger.debug('{} - Changing debug_mode to {}'.format(cls, mode))

    def debug_mode(self):
        return self.__class__._debug_mode
