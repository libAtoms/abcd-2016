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
    def list(self, auth_token):
        """
        List all the databases the user has access to

        :param AuthToken auth_token: Authorisation token
        :rtype: list
        """
        pass

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
    def update(self, auth_token, atoms, upsert, replace):
        """
        Take the atoms object and find an entry in the database with
        the same unique id. If one exists, the old entry gets updated 
        with the new entry.

        :param AuthToken auth_token: Authorisation token
        :param atoms: Atoms to insert
        :type atoms: Atoms or Atoms iterable
        :param bool upsert: Insert configurations even if they don't correspond to any existing ones
        :param bool replace: If a given configuration already exists, replace it
        :return:
        :rtype: UpdateResult
        """
        pass

    @abstractmethod
    def remove(self, auth_token, filter, just_one):
        """
        Remove entries from the databse that match the filter

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter (in MongoDB query language)
        :type filter: dictionary?
        :param bool just_one: remove not more than one entry
        :return: Returns a result that holds the number of removed
            entries and a message
        :rtype: RemoveResult
        """
        pass

    @abstractmethod
    def find(self, auth_token, filter, sort, reverse, limit, keys, omit_keys):
        """
        Find entries that match the filter

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter
        :type filter: list of Conditions
        :param list sort: Sort in increasing order
        :param bool reverse: Reverse the sorting order
        :param int limit: limit the number of returned entries
        :param list keys: keys to be returned. Empty for all
        :param list keys: keys to be omitted
        :return:
        :rtype: Iterator to the Atoms object
        """
        pass

    @abstractmethod
    def add_keys(self, auth_token, filter, kvp):
        """
        Adds key-value pairs to the selectd configurations

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter (in MongoDB query language)
        :type filter: dictionary?
        :param dict kvp: Key-value pairs to be added
        :rtype: AddKvpResult
        """
        pass

    @abstractmethod
    def remove_keys(self, auth_token, filter, keys):
        """
        Removes specified keys from selected configurations

        :param AuthToken auth_token: Authorisation token
        :param filter: Filter (in MongoDB query language)
        :type filter: dictionary?
        :param dict keys: Keys to be removed
        :rtype: RemoveKeysResult
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


class WriteError(Exception):
    """Error which is raised by the backend if write fails"""
    def __init__(self, message):
        self.message = message
        super(WriteError, self).__init__(message)


class ReadError(Exception):
    """Error which is raised by the backend if read fails"""
    def __init__(self, message):
        self.message = message
        super(ReadError, self).__init__(message)

class CommunicationError(Exception):
    """Error which is raised by the backend if communication with remote fails"""
    def __init__(self, message):
        self.message = message
        super(CommunicationError, self).__init__(message)
