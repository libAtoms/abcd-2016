"""
Testing interaction with config files. These tests trash
existing files so only run on travis.

"""

import os

import pytest

from abcd.config import config_file_exists, create_config_file
from abcd.config import read_config_file

CONFIG_PATH = os.path.join(os.environ['HOME'], '.abcd_config')

# Important! This skips all tests in the module!
pytestmark = pytest.mark.skipif(os.getenv('TRAVIS') != 'true',
                                reason="Overwrites config files.")


def test_exists():
    # Need to delete the config file since abcd likes to recreate it
    try:
        os.remove(CONFIG_PATH)
    except:
        pass
    assert config_file_exists() == False
    config_file = open(CONFIG_PATH, 'w')
    config_file.close()
    assert config_file_exists() == True
    os.remove(CONFIG_PATH)


def test_create_config():
    try:
        os.remove(CONFIG_PATH)
    except:
        pass
    assert config_file_exists() == False
    create_config_file()
    assert config_file_exists() == True
    os.remove(CONFIG_PATH)


def test_read_config():
    try:
        os.remove(CONFIG_PATH)
    except:
        pass
    no_config = read_config_file()
    assert no_config.has_section('abcd') == False
    create_config_file()
    with_config = read_config_file()
    assert with_config.has_section('abcd') == True
    os.remove(CONFIG_PATH)
