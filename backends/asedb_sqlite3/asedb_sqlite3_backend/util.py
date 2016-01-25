__author__ = 'Patrick Szmucer'

import os
import re
from ConfigParser import SafeConfigParser

reserved_usernames = ['public', 'all', 'local']
CONFIG_PATH = os.path.join(os.environ['HOME'], '.abcd_asedb_config')
AUTHORIZED_KEYS = os.path.join(os.environ['HOME'], '.ssh/authorized_keys')


def get_dbs_path():
    """
    Reads the config file and returns the path to the folder where
    all the databases are stored.
    """

    dbs_path = None
    parser = SafeConfigParser()

    cmd = 'abcd-asedb --setup'

    # Read the config file if it exists
    if os.path.isfile(CONFIG_PATH):
        try:
            parser.read(CONFIG_PATH)
            dbs_path = parser.get('ase-db', 'dbs_path')
        except:
            raise RuntimeError('There were problems reading {}. Did you run {}?'.format(CONFIG_PATH, cmd))
    else:
        raise RuntimeError('Config file does not exist. Run "{}" first'.format(cmd))
    return dbs_path


def add_user(user):
    """
    Adds a user and their public key to ~/.ssh/authorized_keys file and creates
    directories $databases/USER and $databases/USER_readonly.
    """

    if user in reserved_usernames:
        print 'Error: username "{}" is reserved'.format(user)
        return
    if not re.match(r'^[A-Za-z0-9_]+$', user):
        print 'Error: username cannot contain characters which are not alphanumeric or underscores'
        return

    dbs_path = get_dbs_path()
    user_dbs_path = os.path.join(dbs_path, user)

    # Make sure ~/.ssh/authorized_keys file exists
    ssh_dir = os.path.dirname(AUTHORIZED_KEYS)
    if not os.path.isdir(ssh_dir):
        os.makedirs(ssh_dir)
        os.chmod(ssh_dir, 0700)
    if not os.path.isfile(AUTHORIZED_KEYS):
        open(AUTHORIZED_KEYS, 'a').close()
        os.chmod(AUTHORIZED_KEYS, 0644)

    # Add user's credentials to the authorized_keys file
    public_key = raw_input('Enter the ssh public key for {}: '.format(user))
    line = '\ncommand=". ~/.bash_profile && abcd-asedb-server {}" {}'.format(user, public_key)
    with open(AUTHORIZED_KEYS, 'a') as f:
        f.write(line)
    print '  Added a key for user "{}" to {}'.format(user, AUTHORIZED_KEYS)

    # Check if this user already exists
    if os.path.isdir(user_dbs_path):
        print '  Directory for user "{}" already exists under {}'.format(user, user_dbs_path)
    else:
        # Make a directory for the user
        os.mkdir(user_dbs_path)
        print '  Created {}'.format(user_dbs_path)

    # Same, but for read-only
    readonly_dir = user_dbs_path + '_readonly'
    if os.path.isdir(readonly_dir):
        print '  Readonly directory for user "{}" already exists under {}'.format(user, user_dbs_path)
    else:
        os.mkdir(readonly_dir)
        print '  Created {}'.format(readonly_dir)


def setup():
    """
    Create a config file and a directory in which databases will be stored.
    """

    # Check if the config file exists. If it doesn't, create it
    if not os.path.isfile(CONFIG_PATH):
        parser = SafeConfigParser()
        parser.add_section('ase-db')
        with open(CONFIG_PATH, 'w') as cfg_file:
            parser.write(cfg_file)
        print 'Creating a config file at', CONFIG_PATH

    # Read the config file
    parser = SafeConfigParser()
    parser.read(CONFIG_PATH)

    # Make sure that the ase-db section exists
    if not parser.has_section('ase-db'):
        parser.add_section('ase-db')

    set_dbs_path = True
    if parser.has_option('ase-db', 'dbs_path'):
        print 'Your path to the databases folder is', parser.get('ase-db', 'dbs_path')
        response = raw_input('Do you want to change it? [y/n]: ')
        if response not in ['Y', 'y', 'yes']:
            set_dbs_path = False

    # Ask the user for the path to the databases folder
    if set_dbs_path:
        userInput = raw_input('Path for the databases folder (default is ~/abcd_databases): ')
        if not userInput:
            # No input from user. Set a default directory
            userInput = '~/abcd_databases'
        dbs_path = os.path.expanduser(userInput)
        parser.set('ase-db', 'dbs_path', dbs_path)
    else:
        dbs_path = parser.get('ase-db', 'dbs_path')

    with open(CONFIG_PATH, 'w') as cfg_file:
        parser.write(cfg_file)

    # Path to the "all" folder
    all_path = os.path.join(dbs_path, 'all')

     # Check if the "all" directory exists. If not, create it
    if not os.path.isdir(all_path):
        os.makedirs(all_path)
        print '  Created databases directory at {}'.format(dbs_path)
        print '  Your databases will be stored in {}'.format(all_path)
    else:
        print '  Your databases directory already exists at {}'.format(dbs_path)
        print '  Your databases are stored at {}'.format(all_path)


def print_usage():
    print 'Usage: abcd-asedb --setup / --add-user USER'


def main():
    import sys
    args = sys.argv[1:]

    if len(args) == 0:
        print_usage()
    elif args[0] == '--setup' and len(args) == 1:
        setup()
    elif args[0] == '--add-user' and len(args) == 2:
        add_user(args[1])
    else:
        print_usage()
