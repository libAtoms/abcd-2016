"""
Testing interaction with config files. These tests trash
existing files so only run on travis.

"""

import os

import pytest

from abcd.config import ConfigFile

# Important! This skips all tests in the module!
pytestmark = pytest.mark.skipif(os.getenv('TRAVIS') != 'true',
                                reason="Overwrites config files.")


def test_exists():
    config_file = ConfigFile('test')
    config_file.delete()
    assert config_file.exists() == False
    config_test = open(config_file.path, 'w')
    config_test.close()
    assert config_file.exists() == True
    config_file.delete()


def test_create_config_empty():
    config_file = ConfigFile('test')
    config_file.delete()
    assert config_file.exists() == False
    config_file.initialise()
    assert config_file.exists() == True
    config_file.delete()


def test_create_config():
    config_file = ConfigFile('test')
    config_file.delete()
    assert config_file.exists() == False
    config_file.initialise({'test_section': {'test_option': 'test_value'}})
    assert config_file.exists() == True
    assert config_file.has_section('test_section')
    assert config_file.has_option('test_section', 'test_option')
    assert config_file.get('test_section', 'test_option') == 'test_value'
    config_file.delete()


def test_read_config():
    config_file = ConfigFile('test')
    config_file.delete()
    assert config_file.exists() == False
    config_file.initialise({'test_section': {'test_option': 'test_value'}})
    assert config_file.exists() == True
    # re-read the file
    config_file = ConfigFile('test')
    assert config_file.has_section('test_section')
    assert config_file.has_option('test_section', 'test_option')
    assert config_file.get('test_section', 'test_option') == 'test_value'
    config_file.delete()
