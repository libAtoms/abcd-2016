#! /usr/bin/env python
from __future__ import print_function

import os
import sys
import argparse
import subprocess
import tarfile
import StringIO

from ase.utils import plural
from ase.io import read as ase_read
from ase.io import write as ase_write
from ase.db.summary import Summary
from ase.calculators.calculator import get_calculator

# Try to import the interface. If it fails, the script only has limited
# functionality (only remote querying without saving).
try:
    from asedb_sqlite3_backend.asedb_sqlite3_backend import ASEdbSQlite3Backend
    backend_enabled = True
except ImportError:
    backend_enabled = False

if backend_enabled:
    from structurebox import StructureBox
    from authentication import Credentials
    from util import Table

description = ''

examples = '''
    cli.py --remote abcd@gc121mac1 db1.db --show   (display the database)
    cli.py --remote abcd@gc121mac1 db1.db   (display information about available keys)
    cli.py --remote abcd@gc121mac1 db1.db \'energy<0.6,id>4\'   (querying)
    cli.py --remote abcd@gc121mac1 db1.db --extract-original-file --target extracted   (extract files to the extracted/ folder)
    cli.py --remote abcd@gc121mac1 db1.db 1 --write-to-file extr.xyz   (write the first row to the file extr.xyz)
    cli.py db1.db \'energy>0.7\' --count   (count number of selected rows)
    cli.py db1.db \'energy>0.8\' --remove --no-confirmation   (remove selected configurations, don\'t ask for confirmation)
    cli.py --add-from-file source.xyz db1.db   (add file to the database)
    cli.py db1.db --omit-keys 'user,id' --show  (omit keys)
'''

def main(args = sys.argv[1:]):
    if isinstance(args, str):
        args = args.split(' ')
    parser = argparse.ArgumentParser(usage = 'Usage: %%prog [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Examples: ' + examples,
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
    add('--keys', default='++', help='Select only specified keys')
    add('--omit-keys', default='', help='Don\'t select these keys')
    add('--show', action='store_true', help='Show the database')
    add('--store', metavar='DIR', help='Store a directory')
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
            if stdout.isspace():
                warning(stderr)
                return
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
                warning(stderr)
        else:
            print(stdout)
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
            dbs = box.list(token)
            if args.user:
                user = args.user
            else:
                user = 'Local User'
            if dbs:
                print(('Hello, {}. Databases you have access to:').format(user))
                for db in dbs:
                    print('   {}'.format(db))
            else:
                print(('Hello, {}. You don\'t have access to any databases.').format(user))
            return

        if not args.database:
            raise Exception('No database specified')

        # Get the query
        query = args.query
        if query and query.isdigit():
            query = int(query)

        # Decide which keys to show
        if args.keys == '++':
            keys = '++'
        else:
            keys = args.keys.split(',')
        omit_keys = args.omit_keys.split(',')

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
                filename = '-' # stdout
            else:
                filename = args.write_to_file

            if '.' in filename:
                format = filename.split('.')[1]
            else:
                format = None

            nrows = 0
            list_of_atoms = []
            omit = omit_keys + ['original_file_contents']
            for atoms in box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=args.limit,
                                keys=keys, omit_keys=omit):
                list_of_atoms.append(atoms)
                nrows += 1

            if '%' in filename:
                for i, atoms in enumerate(list_of_atoms):
                    ase_write(filename % i, atoms, format=format)
            else:
                if filename == '-':
                    if format is None: format = 'extxyz'
                    filename = sys.stdout
                print(filename, format)
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
                            sort=args.sort, limit=args.limit,
                            keys=['original_file_contents', 'original_file_name']):
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

        elif args.store:
            if ssh:
                warning('Remote adding not yet supported')
                return
            if query:
                warning('Ignoring query:', query)

            rootdir = args.store
            parsed = {}
            aux_files = []
            for root, subFolders, files in os.walk(rootdir):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        parsed[path] = ase_read(path)
                    except IOError:
                        aux_files.append(path)
                    except:
                        pass

            if not parsed:
                raise Exception('No parsable files found under {}'.format(rootdir))

            for config_filename, atoms in parsed.iteritems():
                exclude = parsed.keys()
                def filter_function(tarinfo):
                    if (tarinfo.name in exclude) and (tarinfo.name != config_filename):
                        return None
                    else:
                        return tarinfo

                c = StringIO.StringIO()
                tar = tarfile.open(fileobj=c, mode='w')

                config_name = os.path.basename(config_filename).split('.')[0]
                arcname = rootdir + '-' + config_name
                tar.add(name=rootdir, arcname=arcname, filter=filter_function)
                tar.close()

                atoms.info['original_file_name'] = arcname + '.tar'
                atoms.arrays['original_file_contents'] = c.getvalue()

                box.insert(token, atoms)
                out('Added {0} and {1} auxilary files from {2}'.format(config_filename, len(aux_files), rootdir))

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
            if args.limit == 0:
                lim = 0
            else:
                lim = args.limit + 1
            atoms_it = box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=lim,
                                keys=keys, omit_keys=omit_keys)
            count = atoms_it.count()
            if args.limit != 0 and count > args.limit:
                count = '{}+'.format(count-1)
            else:
                count = str(count)
            print('Found:', count)

        # Show the database
        elif args.show:
            atoms_it = box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=args.limit,
                                keys=keys, omit_keys=omit_keys)
            table = Table(atoms_it)
            print(table)

        # Print info about keys
        else:
            atoms_it = box.find(auth_token=token, filter=query, 
                                sort=args.sort, limit=args.limit,
                                keys=keys, omit_keys=omit_keys)
            table = Table(atoms_it)
            table.print_keys_table()
            
main()

