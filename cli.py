#! /usr/bin/env python
from __future__ import print_function

import os
import sys
import argparse
import subprocess
import tarfile
import StringIO

from abcd.authentication import Credentials
from abcd.structurebox import StructureBox
from abcd.util import atoms2dict, Table

from ase.utils import plural
from ase.io import read as ase_read
from ase.io import write as ase_write
from ase.db.summary import Summary

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
    add('--verbose', action='store_true', default=False)
    add('--quiet', action='store_true', default=False)
    add('--remote', help = 'Specify the remote')
    add('--user', help = argparse.SUPPRESS)
    add('database', nargs='?', help = 'Specify the database')
    add('query', nargs = '?', default = '', help = 'Query')
    add('--remove', action='store_true',
        help='Remove selected rows.')
    add('--list', action = 'store_true', 
        help = 'Lists all the databases you have access to')
    add('--limit', type=int, default=500, metavar='N',
        help='Show only first N rows (default is 500 rows).  Use --limit=0 '
        'to show all.')
    add('--sort', metavar='COL', default=None,
        help='Specify the column to sort the rows by')
    add('--write-to-file', metavar='(type:)filename',
        help='Write selected rows to file(s). Include format string for multiple \nfiles, e.g. file_%%03d.xyz')
    add('--extract-original-file', action='store_true',
        help='Extract an original file stored with -o/--store-original-file')
    add('--add-from-file', metavar='(type:)filename...',
        help='Add results from file.')
    add('--count', action='store_true',
        help='Count number of selected rows.')
    add('--no-confirmation', action='store_true',
        help='Don\'t ask for confirmation')
    add('--target', default='.', help='Target directory for saving files')
    add('--keys', action='store_true', help='Display information about available keys')
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

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0:
            print(*args)

    def warning(*objs):
        '''Prints the warning to stderr'''
        print(*objs, file=sys.stderr)

    # User specified the "user" argument, quit.
    if args.user and args.remote:
        warning('Unknown option --user. Terminating')
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

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        # An error occured at the remote end when running the command.
        # Print stdout sa it might contain the error.
        if process.returncode:
            warning('An error occured')
            print(stdout)

        # Write the received string to a file
        elif args.write_to_file:
            filename = args.write_to_file
            with open(filename, 'w') as f:
                f.write(stdout)

        # Unpack the received tar
        elif args.extract_original_file:
            s = StringIO.StringIO(stdout)
            try:
                tar = tarfile.open(fileobj=s, mode='r')
                no_files = len(tar.getmembers())
                print('Writing {} files to {}/'.format(no_files, args.target))
                tar.extractall(path=args.target)
            except tarfile.ReadError:
                warning('Received file could not be read')
                return
            except tarfile.ExtractError:
                warning('Could not extract configurations')
                return
            except:
                warning('A fatal error occured')
                return
            finally:
                tar.close()
        else:
            print(stdout)

        # Print any warnings
        warning(stderr)

    else:
        # Detect if the script is running over ssh
        if not args.user and not args.remote:
            ssh = False
        else:
            ssh = True

        if not backend_enabled:
            raise Exception('The backend could not be imported')

        # Try to initialise the backend
        try:
            box = StructureBox(ASEdbSQlite3Backend(database=args.database, user=args.user))
            token = box.authenticate(Credentials(args.user))
        except Exception as e:
            print('An error occured: ', str(e))
            return

        # List all available databases
        if args.list:
            print(box.list_databases())
            return

        # Beyond this point a database has to be specified
        if not args.database:
            raise Exception('No database specified')

        # Get the query
        query = args.query
        if query and query.isdigit():
            query = int(query)

        # Remove entries from a database
        if args.remove:
            if ssh:
                warning('Remote removing not yet supported')
                return
            result = box.remove(token, query, just_one=False, 
                                confirm=not args.no_confirmation)
            print(result.msg)

        # Extract a configuration from the database and write it
        # to the specified file.
        elif args.write_to_file:
            if ssh:
                filename = '-'
            else:
                filename = args.write_to_file

            if '.' in filename:
                format = filename.split('.')[1]
            else:
                format = None

            nrows = 0
            list_of_atoms = []
            for atoms in box.find(auth_token=token, filter=query, 
                            sort=args.sort, limit=args.limit):
                if 'original_file_contents' in atoms.info:
                    del atoms.info['original_file_contents']
                list_of_atoms.append(atoms)
                nrows += 1

            if '%' in filename:
                for i, atoms in enumerate(list_of_atoms):
                    ase_write(filename % i, atoms, format=format)
            else:
                if filename == '-':
                    if format is None: format = 'extxyz'
                    filename = sys.stdout
                ase_write(filename, list_of_atoms, format=format)
            if not ssh:
                out('Wrote %d rows.' % len(list_of_atoms))

        # Extract original file(s) from the database and write them
        # to the directory specified by the --target argument 
        # (current directory by default).
        elif args.extract_original_file:

            # If over ssh, create a tar file in memory
            if ssh:
                c = StringIO.StringIO()
                tar = tarfile.open(fileobj=c, mode='w')

            nwrite = 0
            nat = 0
            skipped_configs = []
            for atoms in box.find(auth_token=token, filter=query, 
                            sort=args.sort, limit=args.limit):
                nat += 1
                if ('original_file_name' not in atoms.info or
                    'original_file_contents' not in atoms.info):
                    skipped_configs.append(nat)
                    continue
                
                original_file_name = atoms.info['original_file_name']
                # Restore to current working directory
                original_file_name = os.path.basename(original_file_name)

                # Add the file to the tar file
                if ssh:
                    filestring = StringIO.StringIO(atoms.info['original_file_contents'])
                    info = tarfile.TarInfo(name=original_file_name)
                    info.size=len(filestring.buf)
                    tar.addfile(tarinfo=info, fileobj=filestring)
                # Write the file locally
                else:
                    new_path = os.path.join(args.target, original_file_name)

                    if not os.path.exists(os.path.dirname(new_path)):
                        os.makedirs(os.path.dirname(new_path))
                    elif os.path.exists(new_path):
                        print('{} already exists, skipping write.'.format(new_path))
                        continue

                    out('Writing %s' % new_path)            
                    with open(new_path, 'w') as original_file:
                        original_file.write(atoms.info['original_file_contents'])
                nwrite += 1

            msg = 'Extracted original output files for %d/%d selected configurations' % (nwrite, nat)
            if skipped_configs:
                msg += '\nNo original file stored for configurations {}'.format(skipped_configs)

            if ssh:
                print(c.getvalue())
                warning(msg)
                tar.close()
            else:
                out(msg)

        # Add a configuration from a file to the specified database
        elif args.add_from_file:
            if ssh:
                warning('Remote adding not yet supported')
                return
            if query:
                warning('Ignoring query:', query)

            filename = args.add_from_file
            if ':' in filename:
                calculator_name, filename = filename.split(':')
                atoms = get_calculator(calculator_name)(filename).get_atoms()
            else:
                atoms = ase_read(filename)
                if isinstance(atoms, list):
                    raise RuntimeError('multi-config file formats not yet supported')

            with open(filename) as f:
                original_file_contents = f.read()
            atoms.info['original_file_name'] = filename
            atoms.arrays['original_file_contents'] = original_file_contents

            box.insert(token, atoms)
            out('Added {0} from {1}'.format(atoms.get_chemical_formula(), filename))

        # Count selected configuration
        elif args.count:
            atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, limit=args.limit)
            print(plural(atoms_it.count(), 'row'))

        elif args.keys:
            atoms_it = box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=args.limit)
            table = Table(atoms_it)
            union = table.keys_union()
            intersection = table.keys_intersection()

            ranges = {}
            for key in union:
                ranges[key] = table.values_range(key)

            print('Union of keys:')
            for key in union:
                print('    {}: {}'.format(key, ranges[key]))

            print('Intersection of keys:')
            for key in intersection:
                print('    {}: {}'.format(key, ranges[key]))
           
        # If there was a query, print number of configurations found
        # If there was no query, print the whole database
        else:    
            atoms_it = box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=args.limit)
            table = Table(atoms_it)
            print(table)
            
main()

