import os
from ConfigParser import SafeConfigParser

CONFIG_PATH = os.path.join(os.environ['HOME'], '.abcd_config')


def config_file_exists():
    if os.path.isfile(CONFIG_PATH):
        return True
    else:
        return False


def create_config_file():
    cfg_parser = SafeConfigParser()
    cfg_parser.add_section('abcd')
    cfg_parser.set('abcd', 'opts', "''")
    cfg_parser.set('abcd', 'backend_module', "")
    cfg_parser.set('abcd', 'backend_name', "")
    with open(CONFIG_PATH, 'w') as cfg_file:
        cfg_parser.write(cfg_file)


def read_config_file():
    cfg_parser = SafeConfigParser()
    cfg_parser.read(CONFIG_PATH)
    return cfg_parser