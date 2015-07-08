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
        """
        Take the Atoms object or an iterable to the Atoms and insert it
        to the database

        :param AuthToken auth_token: Authorisation token
        :param atoms: Atoms to insert
        :type atoms: Atoms or Atoms iterable
        :return: Returns a result that holds a list of ids at which 
            the objects were inserted and a message
        :rtype: InsertResult
        """
        pass

    @abstractmethod
    def update(self, auth_token, atoms):
        '''
        Take the atoms object and find an entry in the database with 
        the same unique id. If one exists, the old entry gets updated 
        with the new entry.
        :param AuthToken auth_token: Authorisation token
        :param atoms: Atoms to insert
        :type atoms: Atoms or Atoms iterable
        :return:
        :rtype: UpdateResult
        '''
        pass

    @abstractmethod
    def remove(self, auth_token, filter, just_one, confirm):
        """
        Remove entries from the databse that match the filter

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter (in MongoDB query language)
        :type filter: dictionary?
        :param bool just_one: remove not more than one entry
        :param bool confirm: confirm before removing
        :return: Returns a result that holds the number of removed
            entries and a message
        :rtype: RemoveResult
        """
        pass

    @abstractmethod
    def find(self, auth_token, filter, sort, limit):
        """
        Find entries that match the filter

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter (in MongoDB query language)
        :type filter: dictionary?
        :param sort: Sort by
        :type sort: string?
        :param int limit: limit the number of returned entries
        :return:
        :rtype: Iterator to the Aoms object
        """
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