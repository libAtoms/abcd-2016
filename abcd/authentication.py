"""
Classes related to facilitating authentication by the backend of some
credentials gathered by the frontend.
"""

__author__ = 'Martin Uhrin'

from abc import ABCMeta
from abc import abstractproperty
import base64


class AuthToken(object):
    def __init__(self, username):
        self._username = username

    @property
    def username(self):
        return self._username


class Credentials(object):
    def __init__(self, username=None):
        """
        Create a credentials object.

        :param username: The username, can be None
        :return: None
        """
        self._username = username

    @property
    def username(self):
        """
        Get the username

        :return: The username
        """
        return self._username


class UsernameAndPassword(Credentials):
    def __init__(self, username, password):
        # Use b64 encoding just to loosely hide the password so it's not
        # visible during debugging etc.
        # WARNING: This provides no security, just mild obfuscation from a
        # glancing user
        self.password = base64.b64encode(password)
        super(Credentials, UsernameAndPassword).__init__(username)

    @property
    def password(self):
        return base64.b64decode(self.password)