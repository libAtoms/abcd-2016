"""
Simple unit tests for abcd.authentication
"""

import pytest

from abcd.authentication import UsernameAndPassword


@pytest.fixture()
def username_and_password():
    initialised = UsernameAndPassword('test_user', 'test_password')
    return initialised


def test_username(username_and_password):
    assert username_and_password.username == 'test_user'


def test_password(username_and_password):
    assert username_and_password.password == 'test_password'
