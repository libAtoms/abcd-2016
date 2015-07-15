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
from ase.db.core import convert_str_to_float_or_str

try:
    from asedb_sqlite3_backend.asedb_sqlite3_backend import ASEdbSQlite3Backend
    backend_enabled = True
except ImportError as e:
    backend_enabled = False
    backend_import_err = str(e)

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
    add('--add-kvp', metavar='{K1=V1,...}', help='Add key-value pairs')
    add('--remove-keys', metavar='K1,K2,...', help='Remove keys')
    args = parser.parse_args()

    # Calculate the verbosity
    verbosity = 1 - args.quiet + args.verbose

    try:
        run(args, verbosity)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x), file=sys.stderr)
            sys.exit(1)
        else:
            raise

def init_backend(db, user):
    if not backend_enabled:
        raise ImportError(backend_import_err)

    # Initialise the backend
    box = StructureBox(ASEdbSQlite3Backend(database=db, user=user))
    token = box.authenticate(Credentials(user))

    return box, token

def communicate_via_ssh(host, sys_args, tty, data_out=None):
    if tty:
        tty_flag = '-t'
        stdout = None
        stderr = None
    else:
        tty_flag = '-T'
        stdout=subprocess.PIPE
        stderr=subprocess.PIPE

    if data_out and not data_out.isspace():
        ssh_call = 'echo \'{}\' | ssh -q {} {} '.format(data_out, tty_flag, host)
    else:
        ssh_call = 'ssh -q {} {} '.format(tty_flag, host)

    # Remove the 'remote' argument
    for arg in ['--remote', '-remote', '--r', '-r']:
        while arg in sys_args:
            pos = sys_args.index(arg)
            sys_args = sys_args[:pos] + sys_args[pos + 2:]

    arguments = ' '.join(sys_args[1:])
    arguments = '\' {}\''.format(arguments)
    command = ssh_call + arguments

    process = subprocess.Popen(command, shell=True, stdout=stdout, stderr=stderr)
    stdout, stderr = process.communicate()

    return stdout, stderr, process.returncode

def run(args, verbosity):

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0:
            print(*(arg.rstrip('\n') for arg in args))

    def to_stderr(*args):
        '''Prints to stderr'''
        if args and any(not arg.isspace() for arg in args):
            print(*(arg.rstrip('\n') for arg in args), file=sys.stderr)

    # Detect if the script is running over ssh
    if not args.user and not args.remote:
        ssh = False
        local = True
    elif not args.user and args.remote:
        ssh = True
        local = True
    elif args.user and not args.remote:
        ssh = True
        local = False
    else:
        raise RuntimeError('Unknown option --user. Terminating')
        sys.exit()

    # List all available databases
    if args.list and ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)
        return

    elif args.list:
        box, token = init_backend(args.database, args.user)

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

    # Get kvp
    kvp = {}
    if args.add_kvp:
        for pair in args.add_kvp.split(','):
            k, v = pair.split('=')
            kvp[k] = convert_str_to_float_or_str(v)

    # Get keys to be removed
    remove_keys = []
    if args.remove_keys:
        for key in args.remove_keys.split(','):
            remove_keys.append(key)


    if args.remove and ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)

    # Remove entries from a database
    elif args.remove:
        box, token = init_backend(args.database, args.user)
        result = box.remove(token, query, just_one=False, 
                            confirm=not args.no_confirmation)
        print(result.msg)

    elif args.write_to_file and ssh and local:
        stdout, stderr, ret = communicate_via_ssh(args.remote, sys.argv, tty=False)

        if stderr and not stderr.isspace():
            to_stderr(stderr)
        if ret or stdout.isspace():
            return

        # Write the received string to a file
        filename = args.write_to_file
        with open(filename, 'w') as f:
            f.write(stdout)

    # Extract a configuration from the database and write it
    # to the specified file.
    elif args.write_to_file:
        box, token = init_backend(args.database, args.user)

        if ssh and not local:
            filename = '-' # stdout
        elif not ssh and local:
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
            ase_write(filename, list_of_atoms, format=format)
        if not ssh:
            out('Wrote %d rows.' % len(list_of_atoms))


    elif args.extract_original_file and ssh and local:
        stdout, stderr, ret = communicate_via_ssh(args.remote, sys.argv, tty=False)

        if stderr and not stderr.isspace():
            to_stderr(stderr)
        if ret or stdout.isspace():
            return

        s = StringIO.StringIO(stdout)
        try:
            tar = tarfile.open(fileobj=s, mode='r')
            no_files = len(tar.getmembers())
            print('Writing {} files to {}/'.format(no_files, args.target))
            tar.extractall(path=args.target)
        except Exception as e:
            to_stderr(str(e))
            return
        finally:
            tar.close()

    # Extract original file(s) from the database and write them
    # to the directory specified by the --target argument 
    # (current directory by default).
    elif args.extract_original_file:

        box, token = init_backend(args.database, args.user)

        # If over ssh, create a tar file in memory
        if ssh and not local:
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
            if ssh and not local:
                filestring = StringIO.StringIO(atoms.info['original_file_contents'])
                info = tarfile.TarInfo(name=original_file_name)
                info.size = len(filestring.buf)
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

        if ssh and not local:
            print(c.getvalue())
            to_stderr(msg)
            tar.close()
        else:
            out(msg)

    elif args.store:
        '''if ssh:
            data_in = sys.stdin
            print('Received:')
            for line in data_in:
                print(line)
            return'''
        if query:
            to_stderr('Ignoring query:', query)

        if ssh or not local:
            return

        box, token = init_backend(args.database, args.user)

        rootdir = args.store
        parsed = []
        aux_files = []
        for root, subFolders, files in os.walk(rootdir):
            for f in files:
                path = os.path.join(root, f)
                try:
                    atoms = ase_read(path, index=slice(0, None, 1))
                except IOError:
                    aux_files.append(path)
                    continue
                except:
                    # Sometimes ASE doesn't catch exceptions while reading
                    # files and IOError is not raised.
                    aux_files.append(path)
                    continue

                if len(atoms) > 1:
                    for at in atoms:
                        parsed.append((path, at, False))
                else:
                    parsed.append((path, atoms[0], True))

        if not parsed:
            raise Exception('No parsable files found under {}'.format(rootdir))

        for config_filename, atoms, attach in parsed:

            exclude = [tup[0] for tup in parsed]
            if attach:
                exclude.remove(config_filename)

            def exclude_fn(name):
                if name in exclude:
                    return True
                else:
                    return False

            c = StringIO.StringIO()
            tar = tarfile.open(fileobj=c, mode='w')

            config_name = os.path.basename(config_filename).split('.')[0]
            arcname = rootdir + '-' + config_name
            tar.add(name=rootdir, arcname=arcname, exclude=exclude_fn)
            tar.close()

            atoms.info['original_file_name'] = arcname + '.tar'
            atoms.arrays['original_file_contents'] = c.getvalue()

            box.insert(token, atoms, kvp)
            if attach:
                out(' -> Added {} and {} auxilary files from {}'
                    .format(config_filename, len(aux_files), rootdir))
            else:
                out(' -> Added {} auxilary files from {} (not attaching {} - multiconfig file)'
                    .format(len(aux_files), rootdir, config_filename))

    # Add a configuration from a file to the specified database
    elif args.add_from_file:

        if query:
            to_stderr('Ignoring query:', query)

        if ssh or not local:
            return

        box, token = init_backend(args.database, args.user)

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

        box.insert(token, atoms, kvp)
        out('Added {0} from {1}'.format(atoms.get_chemical_formula(), filename))

    elif args.add_kvp:
        if ssh and local:
            communicate_via_ssh(args.remote, sys.argv, tty=True)
        else:
            box, token = init_backend(args.database, args.user)
            result = box.add_kvp(token, query, kvp)
            print(result.msg)

    elif args.remove_keys:
        if ssh and local:
            communicate_via_ssh(args.remote, sys.argv, tty=True)
        else:
            box, token = init_backend(args.database, args.user)
            result = box.remove_keys(token, query, remove_keys)
            print(result.msg)

    elif args.count and ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)

    # Count selected configurations
    elif args.count:
        box, token = init_backend(args.database, args.user)

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
    
    elif args.show and ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)

    # Show the database
    elif args.show:
        box, token = init_backend(args.database, args.user)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, limit=args.limit,
                            keys=keys, omit_keys=omit_keys)
        table = Table(atoms_it)
        print(table)

    elif ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)

    elif not args.database:
        to_stderr('No database specified')

    # Print info about keys
    else:
        box, token = init_backend(args.database, args.user)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, limit=args.limit,
                            keys=keys, omit_keys=omit_keys)
        table = Table(atoms_it)
        table.print_keys_table()
            
main()

