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
from ase.atoms import Atoms

try:
    from asedb_sqlite3_backend.asedb_sqlite3_backend import ASEdbSQlite3Backend
    backend_enabled = True
except ImportError as e:
    backend_enabled = False
    backend_import_err = str(e)

if backend_enabled:
    from structurebox import StructureBox
    from authentication import Credentials
    from query import QueryTranslator
    from util import Table, atoms2plaindict, plaindict2atoms
    import json
    from base64 import b64encode, b64decode

description = ''

examples = '''
    cli.py --remote abcd@gc121mac1 db1.db --show   (display the database)
    cli.py --remote abcd@gc121mac1 db1.db   (display information about available keys)
    cli.py --remote abcd@gc121mac1 db1.db \'energy<0.6 id>4 id<20 id!=10,11,12\'   (querying)
    cli.py --remote abcd@gc121mac1 db1.db --extract-files --target extracted/   (extract original files to the extracted/ folder)
    cli.py --remote abcd@gc121mac1 db1.db 1 --write-to-file extr.xyz   (write the first row to the file extr.xyz)
    cli.py db1.db \'energy>0.7\' --count   (count number of selected rows)
    cli.py db1.db \'energy>0.8\' --remove --no-confirmation   (remove selected configurations, don\'t ask for confirmation)
    cli.py db1.db --store conf1.xyz conf2.xyz info.txt   (store original files in the database)
    cli.py db1.db --store configs/   (store the whole directory in the database)
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
    add('database', nargs='?', help = 'Specify the database')
    add('query', nargs = '*', default = '', help = 'Query')
    add('--verbose', action='store_true', default=False)
    add('--quiet', action='store_true', default=False)
    add('--remote', help = 'Specify the remote')
    add('--user', help = argparse.SUPPRESS)
    add('--ssh', action='store_true', default=False, help=argparse.SUPPRESS)
    add('--list', action = 'store_true', 
        help = 'Lists all the databases you have access to')
    add('--show', action='store_true', help='Show the database')
    add('--limit', type=int, default=500, metavar='N',
        help='Show only first N rows (default is 500 rows).  Use --limit=0 '
        'to show all.')
    add('--sort', metavar='COL', default=None,
        help='Specify the column to sort the rows by. Default is increasing order \n(change it using --reverse)')
    add('--reverse', action='store_true', default=False, help='Reverses the sorting order')
    add('--count', action='store_true',
        help='Count number of selected rows.')
    add('--keys', default='++', help='Select only specified keys')
    add('--omit-keys', default='', help='Don\'t select these keys')
    add('--add-kvp', metavar='{K1=V1,...}', help='Add key-value pairs')
    add('--remove-keys', metavar='K1,K2,...', help='Remove keys')
    add('--remove', action='store_true',
        help='Remove selected rows.')
    add('--no-confirmation', action='store_true',
        help='Don\'t ask for confirmation')
    add('--store', metavar='', nargs='+', help='Store a directory / list of files')
    add('--extract-files', action='store_true',
        help='Extract original files stored with --store')
    add('--untar', action='store_true', default=False,
        help='Automaticall untar files extracted with --extract-files')
    add('--target', default='.', help='Target directory for extracted files')
    add('--write-to-file', metavar='(type:)filename',
        help='Write selected rows to file(s). Include format string for multiple \nfiles, e.g. file_%%03d.xyz')
    add('--ids', action='store_true', help='Print unique ids of selected configurations')

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
        ssh_call = 'echo {} | ssh -q {} {} '.format(b64encode(data_out), tty_flag, host)
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

def to_stderr(*args):
    '''Prints to stderr'''
    if args and any(not arg.isspace() for arg in args):
        print(*(arg.rstrip('\n') for arg in args), file=sys.stderr)

def untar_file(fileobj, target, quiet=False):
    try:
        tar = tarfile.open(fileobj=fileobj, mode='r')
        members = tar.getmembers()
        no_files = len(members)
        if not quiet:
            print('  -> Writing {} files to {}/'.format(no_files, target))
        tar.extractall(path=target)
        return [os.path.join(target, m.name) for m in members]
    except Exception as e:
        to_stderr(str(e))
        return None
    finally:
        tar.close()

def run(args, verbosity):

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0:
            print(*(arg.rstrip('\n') for arg in args))

    # Detect if the script is running over ssh
    if args.ssh:
        local = False
        ssh = True
    else:
        local = True
        if args.remote:
            ssh = True
        else:
            ssh = False

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
    q = QueryTranslator(*args.query)
    query = q.translate()

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

        s = StringIO.StringIO(stdout)
        untar_file(s, args.target)

    # Extract a configuration from the database and write it
    # to the specified file.
    elif args.write_to_file:
        box, token = init_backend(args.database, args.user)

        filename = args.write_to_file
        if '.' in filename:
            filename, format = filename.split('.')
        else:
            format = 'extxyz'
        if format == 'xyz':
            format = 'extxyz'

        if ssh and not local:
            tarstring = StringIO.StringIO()
            tar = tarfile.open(fileobj=tarstring, mode='w')

        nrows = 0
        list_of_atoms = []
        omit = omit_keys + ['original_file_contents']
        for atoms in box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit):
            list_of_atoms.append(atoms)
            nrows += 1

        if not list_of_atoms:
            to_stderr('No atoms selected')
            return

        if '%' not in filename and len(list_of_atoms) != 1:
            to_stderr('Please specify the name formatting')
            return

        for i, atoms in enumerate(list_of_atoms):
            if '%' in filename:
                name = filename % i + '.' + format
            else:
                name = filename + '.' + format

            if ssh and not local:
                # For some reason tarring oesn't work
                # if temp_s is used directly in the
                # tar.addfile function. For this reason 
                # the contents of temp_s are transferred
                # to s.
                temp_s = StringIO.StringIO()
                ase_write(temp_s, atoms, format=format)
                s = StringIO.StringIO(temp_s.getvalue())
                temp_s.close()

                info = tarfile.TarInfo(name=name)
                info.size = len(s.buf)
                tar.addfile(tarinfo=info, fileobj=s)
                s.close()
            else:
                ase_write(name, atoms, format=format)

        if ssh and not local:
            print(tarstring.getvalue())
            tar.close()
        else:
            out('Wrote {} rows.'.format(len(list_of_atoms)))

    # Receives the tar file and untars it
    elif args.extract_files and ssh and local:
        stdout, stderr, ret = communicate_via_ssh(args.remote, sys.argv, tty=False)

        if stderr and not stderr.isspace():
            to_stderr(stderr)
        if ret or stdout.isspace():
            return

        s = StringIO.StringIO(stdout)
        members = untar_file(s, args.target, quiet=args.untar)

        # Untar individual tarballs
        if args.untar:
            for tarball in members:
                with open(tarball, 'r') as f:
                    untar_file(f, args.target, quiet=False)

    # Extract original file(s) from the database and write them
    # to the directory specified by the --target argument 
    # (current directory by default), or print the file
    # to stdout.
    elif args.extract_files:
        box, token = init_backend(args.database, args.user)

        # If over ssh, create a tar file in memory
        if ssh and not local:
            c = StringIO.StringIO()
            tar = tarfile.open(fileobj=c, mode='w')

        # Extract original file contents from the atoms
        names = []
        unique_ids = []
        original_files =[]
        nat = 0
        for atoms in box.find(auth_token=token, filter=query, 
                        sort=args.sort, reverse=args.reverse,
                        limit=args.limit,
                        keys=['original_file_contents', 'unique_id']):
            nat += 1
            if 'original_file_contents' not in atoms.info:
                skipped_configs.append(nat)
                continue
            name = atoms.get_chemical_formula()
            if len(name) > 10:
                name = str[:10]
            names.append(name)
            unique_ids.append(atoms.info['unique_id'])
            original_files.append(atoms.info['original_file_contents'])

        # Mangle the names
        for name in names:
            indices = [i for i, s in enumerate(names) if s == name]
            if len(indices) > 1:
                for i in indices:
                    names[i] += '-' + unique_ids[i][-15:]
        
        nwrite = 0
        skipped_configs = []
        for i in range(len(names)):
            # Add the file to the tar file which will
            # be printed to stdout.
            if ssh and not local:
                filestring = StringIO.StringIO(b64decode(original_files[i]))
                info = tarfile.TarInfo(name=names[i]+'.tar')
                info.size = len(filestring.buf)
                tar.addfile(tarinfo=info, fileobj=filestring)
            # Write the file locally
            else:
                path = os.path.join(args.target, names[i]+'.tar')

                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                elif os.path.exists(path):
                    out('{} already exists. Skipping write'.format(path))

                out('  --> Writing {} files to {}/'.format(path, args.target))            
                with open(path, 'w') as original_file:
                    original_file.write(b64decode(original_files[i]))
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

    # Receive configurations via stdin and write it to the database
    elif args.store and ssh and not local:
        # Authenticate before unpickling received data
        # (only trust known users)
        box, token = init_backend(args.database, args.user)

        data_in = json.loads(b64decode(sys.stdin.read()))

        for dct in data_in[0]:
            dct['atoms'] = plaindict2atoms(dct['atoms'])

        parsed = data_in[0]
        aux_files = data_in[1]

        if not isinstance(parsed, list) or not parsed:
            to_stderr('No atoms received')
            return
        
        for dct in parsed:
            box.insert(token, dct['atoms'], kvp)

        out('  --> Added {} configuration(s) to {}'
                .format(len(parsed), args.database))
        if aux_files:
            out('Auxilary files inclued with each configuration:')
            for f in aux_files:
                out('  ', f)

        not_included = set([dct['config_path'] for dct in parsed if not dct['attach_original']])
        if not_included:
            out('The following original files were not included:')
        for f in not_included:
            out('  ', f)

    elif args.store:
        if query:
            to_stderr('Ignoring query:', query)

        # Detect if the supplied arguments are directories or files
        dirs = []
        files = []
        for arg in args.store:
            if os.path.isdir(arg):
                dirs.append(arg)
            elif os.path.isfile(arg):
                files.append(arg)
            else:
                raise Exception('{} does not exist'.format(arg))
        dirs = list(set(dirs))
        files = list(set(files))

        if dirs and files:
            raise Exception('Supplied arguments have to be either all directories or all files')
        if len(dirs) > 1:
            raise Exception('Storing multiple directories at the same time not yet supported')

        def add_atoms_to_list(config_path, directory, atoms, lst):
            if len(atoms) > 1:
                for at in atoms:
                    lst.append({'config_path':config_path, 'directory':directory, 'atoms':at, 'attach_original':False})
            else:
                lst.append({'config_path':config_path, 'directory':directory, 'atoms':atoms[0], 'attach_original':True})

        def process_dir():
            direct = dirs[0]
            parsed = []
            aux_files = []
            for root, subFolders, files in os.walk(direct):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        atoms = ase_read(path, index=slice(0, None, 1))
                        add_atoms_to_list(path, direct, atoms, parsed)
                    except:
                        aux_files.append(path)
            return parsed, aux_files

        def process_files():
            parsed = []
            aux_files = []
            for f in files:
                try:
                    atoms = ase_read(f, index=slice(0, None, 1))
                    add_atoms_to_list(f, None, atoms, parsed)
                except:
                    aux_files.append(f)
            return parsed, aux_files

        if dirs:
            parsed, aux_files = process_dir()
        else:
            parsed, aux_files = process_files()

        if not parsed:
            raise Exception('Could not find any parsable files')

        # Tar files together and attach the .tar to the
        # corresponding Atoms object.
        for dct in parsed:
            path = dct['config_path']
            directory = dct['directory']
            attach = dct['attach_original']

            exclude = set([d['config_path'] for d in parsed])
            if attach:
                exclude.remove(path)

            def exclude_fn(name):
                if name in exclude:
                    return True
                else:
                    return False

            c = StringIO.StringIO()
            tar = tarfile.open(fileobj=c, mode='w')

            tar_empty = False
            if directory:
                # Tar the directory
                tar.add(name=directory, exclude=exclude_fn)
                tar.close()
            else:
                # Tar all the files together
                for f in files:
                    tar.add(name=f, exclude=exclude_fn)
                if not tar.getmembers():
                    tar_empty = True
                tar.close()

            # Attach original file to the Atoms object
            if not tar_empty:
                dct['atoms'].arrays['original_file_contents'] = b64encode(c.getvalue())

        if ssh and local:
            # Convert the atoms objects to dictionaries
            data_out = [parsed, aux_files]
            for dct in data_out[0]:
                dct['atoms'] = atoms2plaindict(dct['atoms'])

            # Serialise the data and send it to remote
            data_string = json.dumps(data_out)
            communicate_via_ssh(args.remote, sys.argv, tty=True, data_out=data_string)
        else:
            # Write atoms to the database
            box, token = init_backend(args.database, args.user)
            atoms_list = [dct['atoms'] for dct in parsed]
            box.insert(token, atoms_list, kvp)

            out('  --> Added {} configuration(s) to {}'
                .format(len(parsed), args.database))
            if aux_files:
                out('Auxilary files inclued with each configuration:')
                for f in aux_files:
                    out('  ', f)

            not_included = set([dct['config_path'] for dct in parsed if not dct['attach_original']])
            if not_included:
                out('The following original files were not included:')
            for f in not_included:
                out('  ', f)

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
                            sort=args.sort, reverse=args.reverse,
                            limit=lim, keys=keys, omit_keys=omit_keys)
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
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        table = Table(atoms_it)
        print(table)

    elif ssh and local:
        communicate_via_ssh(args.remote, sys.argv, tty=True)

    elif not args.database:
        to_stderr('No database specified')

    elif args.ids:
        box, token = init_backend(args.database, args.user)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        for atoms in atoms_it:
            print(atoms.info['unique_id'])

    # Print info about keys
    else:
        box, token = init_backend(args.database, args.user)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)

        table = Table(atoms_it)
        table.print_keys_table()
            
main()

