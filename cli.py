#! /usr/bin/env python

import os
import sys
import argparse
import subprocess

from abcd.authentication import Credentials
from abcd.structurebox import StructureBox

from ase.utils import plural
from ase.io import read
from ase.db.row import atoms2dict

# Try to import the interface. If it fails, the script only has limited
# functionality (only remote querying without saving).
try:
    from asedb_sqlite3_backend.asedb_sqlite3_backend import ASEdbSQlite3Backend
    backend_enabled = True
except ImportError:
    backend_enabled = False

description = ''

examples = ['']

def main(args = sys.argv[1:]):
    if isinstance(args, str):
        args = args.split(' ')
    parser = argparse.ArgumentParser(usage = 'Usage: %%prog [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Selection examples: ' + ', '.join(examples) + '.',
                        formatter_class=argparse.RawTextHelpFormatter)

    # Display usage if no arguments are supplied
    if len(sys.argv)==1:
        parser.print_usage()
        sys.exit(1)

    add = parser.add_argument
    add('-v', '--verbose', action='store_true', default=False)
    add('-q', '--quiet', action='store_true', default=False)
    add('--remote', help = 'Specify the remote')
    add('-u', '--user', help = argparse.SUPPRESS)
    add('database', nargs='?', help = 'Specify the database')
    add('query', nargs = '?', default = '', help = 'Query')
    add('--remove', action='store_true',
        help='Remove selected rows.')
    add('--list', action = 'store_true', 
        help = 'Lists all the databases you have access to')
    args = parser.parse_args()

    # Calculate the verbosity
    verbosity = 1 - args.quiet + args.verbose

    try:
        run(args, verbosity)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x))
            sys.exit(1)
        else:
            raise

def run(args, verbosity):
    # User specified the "user" argument, quit.
    if args.user and args.remote:
        print 'Unknown option --user. Terminating'
        sys.exit()

    # Query to the remote server. Remove the --remote argumnet and 
    # send the commmand via ssh. Mode: remote
    elif not args.user and args.remote:

        ssh_call = 'ssh {} '.format(args.remote)

        # Remove the 'remote' argument
        for arg in ['--remote', '-remote', '--r', '-r']:
            while arg in sys.argv:
                pos = sys.argv.index(arg)
                sys.argv = sys.argv[:pos] + sys.argv[pos + 2:]

        arguments = ' '.join(sys.argv[1:])
        arguments = '\' {}\''.format(arguments)
        command = ssh_call + arguments
        
        # Execute the ssh command, capture the output
        try:
            output = subprocess.check_output(command, shell=True)
            print output
        except subprocess.CalledProcessError as e:
            print e.output
            sys.exit()

    else:
        if not args.user and not args.remote:
            mode = 'local'
        else:
            mode = 'incoming'

        if not backend_enabled:
            raise Exception('The backend could not be imported')
        box = StructureBox(ASEdbSQlite3Backend(database=args.database, user=args.user))
        token = box.authenticate(Credentials(args.user))

        if args.list:
            print box.list_databases()
            return

        # Beyond this point a database has to be specified
        if not args.database:
            raise Exception('No database specified')

        # Get the query
        query = args.query
        if query and query.isdigit():
            query = int(query)

        if args.remove:
            box.remove(token, query, False)

        else:
            # If there was a query, print number of configurations found
            # If there was no query, print the whole database
            atoms_it = box.find(token, query)
            for at in atoms_it:
                print at

main()
