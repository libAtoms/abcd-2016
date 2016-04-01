"""
config.py

Interact with configuration files and data files.

For testing, set XDG_CONFIG_HOME and XDG_DATA_HOME to avoid destroying
existing files.

"""

import os
from os import path

# PY2 compat
try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

# The appdirs module ensures that we use the correct directories
# on each operating system, e.g. XDG spec for Linux.
from appdirs import user_config_dir, user_data_dir

config_dir = user_config_dir('abcd')
data_dir = user_data_dir('abcd')


class ConfigFile(SafeConfigParser):
    """Generic configuration file for specific parts of the code."""
    def __init__(self, module, *args, **kwargs):
        self.module = module
        self.path = path.join(config_dir, self.module)
        # PY2 old style class can't use super()
        SafeConfigParser.__init__(self, *args, **kwargs)
        self.read(self.path)

    def exists(self):
        """Return True if the config file already exists."""
        if os.path.isfile(self.path):
            return True
        else:
            return False

    def initialise(self, data=None, overwrite=True):
        """
        Create a new configuration file. If data is a dict the new
        configuration file will include the data as
        {section: {key: value}}
        """
        # No clobber option
        if not overwrite and self.exists():
            raise OSError("Will not overwrite existing configuration {0}."
                          "".format(self.path))
        # Might not exist on the first run
        try:
            os.makedirs(config_dir)  # PY2; use exist_ok=True in PY3
        except OSError:
            # Exists
            pass
        # Build up from a blank configuration
        new_config = SafeConfigParser()

        if data is not None:
            for section in data:
                new_config.add_section(section)
                for option, value in data[section].items():
                    new_config.set(section, option, value)

        with open(self.path, 'w') as cfg_file:
            new_config.write(cfg_file)

        # become the new file
        self.read(self.path)

#    def open(self):
#        self.read(self.path)
#        cfg_parser = SafeConfigParser()
#        cfg_parser.read(path.join(config_dir, self.module))
#        return cfg_parser

    def delete(self):
        try:
            os.remove(self.path)
            return True
        except OSError:
            return False
