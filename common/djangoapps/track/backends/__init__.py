"""
Event tracking backend module.

Contains the base class for event trackers, and implementation of some
backends.

"""


import abc

import six


class BaseBackend(metaclass=abc.ABCMeta):
    """
    Abstract Base Class for event tracking backends.

    """

    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def send(self, event):
        """Send event to tracker."""
        pass  # lint-amnesty, pylint: disable=unnecessary-pass
