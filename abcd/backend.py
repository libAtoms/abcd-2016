"""
The backend interface that must be implemented by any structure storage library
that wants to be compliant with this framework.

In general implementations of this class should perform translation from to
commands understood by the native storage format being used be it SQL,
a filesystem, MongoDB or others.
"""

__author__ = 'Martin Uhrin'

from abc import ABCMeta
from abc import abstractmethod


class Backend(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def authenticate(self, credentials):
        """
        Take a set of credentials and return an authorisation token or raise
        an exception

        :param Credentials credentials: The credentials, a subclass of
        :py:class:Credentials
        :return:
        :rtype: AuthToken
        """
        pass

    @abstractmethod
    def insert(self, auth_token, atoms):
        pass

    @abstractmethod
    def remove(self, auth_token, filter, just_one):
        pass

    @abstractmethod
    def find(self, auth_token, filter):
        pass

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def is_open(self):
        pass


class Cursor(object):
    __metaclass__ = ABCMeta

    def __iter__(self):
        return self

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def count(self):
        pass