#! /usr/bin/env python
from __future__ import print_function

import os
import sys
import argparse
import subprocess
import tarfile
import StringIO
from base64 import b64encode, b64decode
import json

from ase.utils import plural
from ase.io import read as ase_read
from ase.io import write as ase_write
from ase.db.summary import Summary
from ase.calculators.calculator import get_calculator
from ase.db.core import convert_str_to_float_or_str
from ase.atoms import Atoms

from structurebox import StructureBox
from authentication import Credentials
from query import translate
from results import UpdateResult, InsertResult
from table import print_keys_table, print_rows
from util import atoms2dict, dict2atoms
from config import read_config_file, create_config_file, config_file_exists

description = ''

examples = '''
    abcd --remote abcd@gc121mac1 db1.db --show   (display the database)
    abcd --remote abcd@gc121mac1 db1.db   (display information about available keys)
    abcd abcd@gc121mac1:db1.db \'energy<0.6 id>4 id<20 id!=10,11,12 elements~C elements~H,F,Cl\'   (querying; remote can be specified using a colon before the database name)
    abcd abcd@gc121mac1:db1.db --extract-original-files --path-prefix extracted/   (extract original files to the extracted/ folder)
    abcd abcd@gc121mac1:db1.db 1 --write-to-file extr.xyz   (write the first row to the file extr.xyz)
    abcd db1.db \'energy>0.7\' --count   (count number of selected rows)
    abcd db1.db \'energy>0.8\' --remove --no-confirmation   (remove selected configurations, don\'t ask for confirmation)
    abcd db1.db --store conf1.xyz conf2.xyz info.txt   (store original files in the database)
    abcd db1.db --store configs/   (store the whole directory in the database)
    abcd db1.db --omit-keys 'user,id' --show  (omit keys)
'''

def main():
    sys_args = sys.argv[1:]
    if isinstance(sys_args, str):
        sys_args = sys_args.split(' ')

    # Detect whether the script is running locallly or not
    # and get the username
    if '--ssh' in sys_args:
        # Running on the remote computer
        local = False
        sys_args.remove('--ssh')

        # Get the username
        if '--user' in sys_args:
            idx = sys_args.index('--user')
            user = sys_args[idx + 1]
            sys_args = sys_args[:idx] + sys_args[idx + 2:]
        else:
            user = 'public'

        # Get the access mode
        if '--readonly' in sys_args:
            readonly = True
            sys_args.remove('--readonly')
        else:
            readonly = False
    else:
        local = True
        user = None
        readonly = False

    if not config_file_exists():
        create_config_file()

    if local:
        # Load the options from the config file. Push them to the front of the list
        # so they will be overwritten on the command line.
        cfg_options = read_config_file().get('abcd', 'opts')
        new_args = []
        if (cfg_options[0] == cfg_options[-1]) and cfg_options.startswith(("'", '"')):
            cfg_options = cfg_options[1:-1]
        for opt in cfg_options.split(' '):
            if opt:
                new_args.append(opt)
        sys_args = new_args + sys_args

    parser = argparse.ArgumentParser(usage = 'Usage: abcd [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Examples: ' + examples,
                        formatter_class=argparse.RawTextHelpFormatter)

    # Display usage if no arguments are supplied
    if len(sys_args) == 0:
        parser.print_usage()

    add = parser.add_argument
    add('database', nargs='?', help = 'Specify the database')
    add('query', nargs = '*', default = '', help = 'Query')
    add('--verbose', action='store_true', default=False)
    add('--quiet', action='store_true', default=False)
    add('--remote', help = 'Specify the remote')
    add('--list', action = 'store_true', 
        help = 'Lists all the databases you have access to')
    add('--show', action='store_true', help='Show the database')
    add('--pretty', action='store_true', default=True, help='Use pretty tables')
    add('--no-pretty', action='store_false', dest='pretty', help='Don\'t use pretty tables')
    add('--limit', type=int, default=0, metavar='N',
        help='Show only first N rows (default is 500 rows).  Use --limit=0 '
        'to show all.')
    add('--sort', metavar='COL', default=None,
        help='Specify the column to sort the rows by. Default is increasing order \n(change it using --reverse)')
    add('--reverse', action='store_true', default=False, help='Reverses the sorting order')
    add('--count', action='store_true',
        help='Count number of selected rows.')
    add('--keys', default='++', help='Select only specified keys')
    add('--omit-keys', default='', help='Don\'t select these keys')
    add('--add-keys', metavar='{K1=V1,...}', help='Add key-value pairs')
    add('--remove-keys', metavar='K1,K2,...', help='Remove keys')
    add('--remove', action='store_true',
        help='Remove selected rows.')
    add('--confirm', action='store_true', default=True,
        help='Require confrmation when removing')
    add('--no-confirm', action='store_false', dest='confirm',
        help='Don\'t ask for confirmation when removing')
    add('--store', metavar='', nargs='+', help='Store a directory / list of files')
    add('--update', metavar='', nargs='+', help='Update the databse with a directory / list of files')
    add('--replace', action='store_true', default=False, 
        help='Replace configurations with the same uid when using --update')
    add('--no-replace', action='store_false', dest='replace', 
        help='Don\'t replace configurations with the same uid when using --update')
    add('--upsert', action='store_true', default=False, 
        help='Insert configurations which are not yet in the database when using --update')
    add('--no-upsert', action='store_false', dest='upsert', 
        help='Don\'t insert configurations which are not yet in the database when using --update')
    add('--extract-original-files', action='store_true',
        help='Extract original files stored with --store')
    add('--untar', action='store_true', default=False,
        help='Automatically untar files extracted with --extract-files')
    add('--no-untar', action='store_false', dest='untar',
        help='Don\'t automatically untar files extracted with --extract-files')
    add('--path-prefix', default='.', help='Path prefix for extracted files')
    add('--write-to-file', metavar='(type:)filename',
        help='Write selected rows to file(s). Include format string for multiple \nfiles, e.g. file_%%03d.xyz')
    add('--ids', action='store_true', help='Print unique ids of selected configurations')

    args = parser.parse_args(sys_args)

    # Do some post-processing
    if args.database is not None and ':' in args.database:
        remote, database = args.database.split(':')
        if args.remote is not None:
            print('Error: Remote specified twice: "--remote {}" and "{}"'.format(args.remote, args.database), file=sys.stderr)
            sys.exit()
        args.remote = remote
        args.database = database

    # For running locally: decide whether the script will open connection
    # to the remote and or run purely locally
    if local:
        if args.remote is not None:
            # Will communicate with remote
            ssh = True
        else:
            # Running entirely locally
            ssh = False
    else:
        ssh = True

    # Calculate the verbosity
    verbosity = 1 - args.quiet + args.verbose

    try:
        run(args, sys_args, verbosity, local, ssh, user, readonly)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x), file=sys.stderr)
            sys.exit(1)
        else:
            raise

def init_backend(db, user, readonly):
    # Get the backend location and name from the config file
    cfg = read_config_file()
    backend_module = cfg.get('abcd', 'backend_module')
    backend_name = cfg.get('abcd', 'backend_name')

    if not backend_module or not backend_name:
        print('  Please specify the backend in ~/.abcd_config')
        sys.exit()

    # Import the backend and other external libraries
    Backend = getattr(__import__(backend_module, fromlist=[backend_name]), backend_name)
    box = StructureBox(Backend(database=db, user=user, readonly=readonly))
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

    arguments = ' '.join(sys_args)
    arguments = '\' {}\''.format(arguments)
    command = ssh_call + arguments

    process = subprocess.Popen(command, shell=True, stdout=stdout, stderr=stderr)
    stdout, stderr = process.communicate()

    return stdout, stderr, process.returncode

def to_stderr(*args):
    '''Prints to stderr'''
    if args and any(not arg.isspace() for arg in args):
        print(*(arg.rstrip('\n') for arg in args), file=sys.stderr)

def untar_file(fileobj, path_prefix, quiet=False):
    try:
        tar = tarfile.open(fileobj=fileobj, mode='r')
        members = tar.getmembers()
        no_files = len(members)
        if not quiet:
            print('  -> Writing {} file(s) to {}/'.format(no_files, path_prefix))
        tar.extractall(path=path_prefix)
        return [os.path.join(path_prefix, m.name) for m in members]
    except Exception as e:
        to_stderr(str(e))
        return None
    finally:
        tar.close()

def untar_and_delete(tar_files, path_prefix):
    # Untar individual tarballs
    for tarball in tar_files:
        with open(tarball, 'r') as f:
            untar_file(f, path_prefix, quiet=True)
        os.remove(tarball)

def print_result(result, parsed, aux_files, database):

    if isinstance(result, UpdateResult):
        n_succ = len(result.updated_ids) + len(result.upserted_ids) + len(result.replaced_ids)

        # Print "10 configuraions were updated:"
        n_upd = len(result.updated_ids)
        if n_upd:
            s1 = 's' if n_upd != 1 else ''
            s2 = 'were' if n_upd != 1 else 'was'
            colon = ':' if n_upd != 0 else ''
            print('{} configuration{} {} updated{}'.format(n_upd, s1, s2, colon))

            # Print ids of updated configurations
            for i in result.updated_ids:
                print('  {}'.format(i))

        # Print "10 configurations were replaced with --replace"
        n_repl = len(result.replaced_ids)
        if n_repl:
            s1 = 's' if n_repl != 1 else ''
            s2 = 'were' if n_repl != 1 else 'was'
            colon = ':' if n_repl != 0 else ''
            print('{} configuration{} {} replaced{}'.format(n_repl, s1, s2, colon))

            # Print ids of replaced configurations
            for i in result.replaced_ids:
                print('  {}'.format(i))

        # Print "13 configurations were not found in the database and were not added (add with --upsert):"
        n_sk = len(result.skipped_ids)
        if n_sk:
            s1 = 's' if n_sk != 1 else ''
            s2 = 'were' if n_sk != 1 else 'was'
            colon = ':' if n_sk != 0 else ''
            print('{} configuration{} {} not found in the database and {} not added (add with --upsert){}'
                .format(n_sk, s1, s2, s2, colon))

            # Print ids of skipped configurations
            for i in result.skipped_ids:
                print('  {}'.format(i))

        # Print "13 configurations were upserted into the database with --upsert:"
        n_ups = len(result.upserted_ids)
        if n_ups:
            s1 = 's' if n_ups != 1 else ''
            s2 = 'were' if n_ups != 1 else 'was'
            colon = ':' if n_ups != 0 else ''
            print('{} configuration{} {} upserted into the database with --upsert{}'
                .format(n_ups, s1, s2, colon))

            # Print ids of upserted configurations
            for i in result.upserted_ids:
                print('  {}'.format(i))

    if isinstance(result, InsertResult):
        n_succ = len(result.inserted_ids)

        # Print "10 configuraions were inserted:"
        n_ins = len(result.inserted_ids)
        s1 = 's' if n_ins != 1 else ''
        s2 = 'were' if n_ins != 1 else 'was'
        colon = ':' if n_ins != 0 else ''
        print('{} configuration{} {} inserted{}'.format(n_ins, s1, s2, colon))

        # Print ids of inserted configurations
        if n_ins:
            for i in result.inserted_ids:
                print('  {}'.format(i))

        # Print "13 configurations were found in the database and were not added"
        n_sk = len(result.skipped_ids)
        if n_sk:
            s1 = 's' if n_sk != 1 else ''
            s2 = 'were' if n_sk != 1 else 'was'
            colon = ':' if n_sk != 0 else ''
            print('{} configuration{} {} found in the database and {} not added{}'
                .format(n_sk, s1, s2, s2, colon))

            # Print ids of skipped configurations
            for i in result.skipped_ids:
                print('  {}'.format(i))

    # Print info about what files were included
    if n_succ:
        if aux_files:
            print('Original files included with each configuration:')
            for f in aux_files:
                print('  ', f)

        not_included = set([dct['config_path'] for dct in parsed if not dct['attach_original']])
        if not_included:
            print('The following files were not included as original files:')
        for f in not_included:
            print('  ', f)

def run(args, sys_args, verbosity, local, ssh, user, readonly):

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0 and args and any(not arg.isspace() for arg in args):
            print(*(arg.rstrip('\n') for arg in args))

    # Get the query
    query = translate(args.query)

    # Decide which keys to show
    if args.keys == '++':
        keys = '++'
    else:
        keys = args.keys.split(',')
    
    omit_keys = args.omit_keys.split(',')
    if '' in omit_keys:
        omit_keys.remove('')

    # Get kvp
    kvp = {}
    if args.add_keys:
        for pair in args.add_keys.split(','):
            k, v = pair.split('=')
            kvp[k] = convert_str_to_float_or_str(v)

    # Get keys to be removed
    remove_keys = []
    if args.remove_keys:
        for key in args.remove_keys.split(','):
            remove_keys.append(key)


    if args.remove and ssh and local:
        communicate_via_ssh(args.remote, sys_args, tty=True)

    # Remove entries from a database
    elif args.remove:
        box, token = init_backend(args.database, user, readonly)
        result = box.remove(token, query, just_one=False, 
                            confirm=args.confirm)
        print(result.msg)

    elif args.write_to_file and ssh and local:
        stdout, stderr, ret = communicate_via_ssh(args.remote, sys_args, tty=False)

        if stderr and not stderr.isspace():
            to_stderr(stderr)
        if ret or stdout.isspace():
            return

        s = StringIO.StringIO(stdout)
        untar_file(s, args.path_prefix)

    # Extract a configuration from the database and write it
    # to the specified file.
    elif args.write_to_file:
        box, token = init_backend(args.database, user, readonly)

        filename = args.write_to_file
        if '.' in filename:
            filename, display_format = filename.split('.')
        else:
            display_format = 'xyz'

        # displayed_format will appear in the file name
        if display_format == 'xyz':
            format = 'extxyz'
        else:
            format = display_format

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

        if '%' not in filename:
            one_file = True
        else:
            one_file = False

        def add_atoms_to_tar(tar, atoms, name, format):
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

        def write_atoms_locally(atoms, name, format, path_prefix):
            if not os.path.exists(path_prefix):
                os.makedirs(path_prefix)
            ase_write(os.path.join(path_prefix, name), atoms, format=format)

        files_written = 0
        if one_file:
            name = filename + '.' + display_format
            if ssh and not local:
                add_atoms_to_tar(tar, list_of_atoms, name, format)
            else:
                write_atoms_locally(list_of_atoms, name, format, args.path_prefix)
                files_written = 1
        else:
            # Write extracted configurations into separate files
            for i, atoms in enumerate(list_of_atoms):
                name = filename % i + '.' + display_format
                if ssh and not local:
                    add_atoms_to_tar(tar, atoms, name, format)
                else:
                    write_atoms_locally(atoms, name, format, args.path_prefix)
                    files_written += 1

        if ssh and not local:
            print(tarstring.getvalue())
            tar.close()
        else:
            out('  -> Writing {} file(s) to {}/'.format(files_written, args.path_prefix))

    # Receives the tar file and untars it
    elif args.extract_original_files and ssh and local:
        stdout, stderr, ret = communicate_via_ssh(args.remote, sys_args, tty=False)

        if stderr and not stderr.isspace():
            to_stderr(stderr)
        if ret or stdout.isspace():
            return

        s = StringIO.StringIO(stdout)
        members = untar_file(s, args.path_prefix, quiet=True)

        # Untar individual tarballs
        if args.untar:
            untar_and_delete(members, args.path_prefix)
            msg = '  Files were untarred to {}/'.format(args.path_prefix)
        else:
            msg = '  Files were written to {}/'.format(args.path_prefix)
        out(msg)

    # Extract original file(s) from the database and write them
    # to the directory specified by the --path-prefix argument 
    # (current directory by default), or print the file
    # to stdout.
    elif args.extract_original_files:
        box, token = init_backend(args.database, user, readonly)

        # If over ssh, create a tar file in memory
        if ssh and not local:
            c = StringIO.StringIO()
            tar = tarfile.open(fileobj=c, mode='w')

        # Extract original file contents from the atoms
        names = []
        unique_ids = []
        original_files =[]
        skipped_configs = []
        nat = 0
        for atoms in box.find(auth_token=token, filter=query, 
                        sort=args.sort, reverse=args.reverse,
                        limit=args.limit,
                        keys=['original_file_contents', 'uid']):
            nat += 1
            if 'original_file_contents' not in atoms.info:
                skipped_configs.append(nat)
                continue
            name = atoms.get_chemical_formula()
            if len(name) > 15:
                name = str[:15]
            names.append(name)
            unique_ids.append(atoms.info['uid'])
            original_files.append(atoms.info['original_file_contents'])

        # Mangle the names
        for name in names:
            indices = [i for i, s in enumerate(names) if s == name]
            if len(indices) > 1:
                for i in indices:
                    names[i] += '-' + str(unique_ids[i])[-15:]

        extracted_paths = []

        # Add the file to the tar file which will
        # be printed to stdout.
        if ssh and not local:
            for i in range(len(names)):
                filestring = StringIO.StringIO(b64decode(original_files[i]))
                info = tarfile.TarInfo(name=names[i]+'.tar')
                info.size = len(filestring.buf)
                tar.addfile(tarinfo=info, fileobj=filestring)
            tar.close()
            print(c.getvalue())

            msg = '  Extracted original files from {} configurations\n'.format(len(names))
            if skipped_configs:
                msg += '  No original files stored for configurations {}'.format(skipped_configs)
            to_stderr(msg)
        else:
            # Write the file locally
            for i in range(len(names)):
                path = os.path.join(args.path_prefix, names[i]+'.tar')

                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                elif os.path.exists(path):
                    out('{} already exists. Skipping write'.format(path))

                with open(path, 'w') as original_file:
                    original_file.write(b64decode(original_files[i]))
                    extracted_paths.append(path)

            msg = '  Extracted original files from {} configurations\n'.format(len(extracted_paths))
            if skipped_configs:
                msg += '  No original files stored for configurations {}\n'.format(skipped_configs)

            # Untar individual tarballs
            if args.untar:
                untar_and_delete(extracted_paths, args.path_prefix)
                msg += '  Files were untarred to {}/'.format(args.path_prefix)
            else:
                msg += '  Files were written to {}/'.format(args.path_prefix)
            out(msg)

    # Receive configurations via stdin and write it to the database
    elif (args.store or args.update) and ssh and not local:
        box, token = init_backend(args.database, user, readonly)

        data_in = json.loads(b64decode(sys.stdin.read()))

        for dct in data_in[0]:
            dct['atoms'] = dict2atoms(dct['atoms'], plain_arrays=True)

        parsed = data_in[0]
        aux_files = data_in[1]

        if not isinstance(parsed, list) or not parsed:
            to_stderr('No atoms received')
            return
        
        if args.store:
            result = box.insert(token, (dct['atoms'] for dct in parsed), kvp)
        else:
            result = box.update(token, (dct['atoms'] for dct in parsed), args.upsert, args.replace)
        print_result(result, parsed, aux_files, args.database)

    elif (args.store or args.update):
        if args.store:
            files_args = args.store
        else:
            files_args = args.update
        
        # Detect if the supplied arguments are directories or files
        dirs = []
        files = []
        for f in files_args:
            if os.path.isdir(f):
                dirs.append(f)
            elif os.path.isfile(f):
                files.append(f)
            else:
                raise Exception('{} does not exist'.format(f))
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
                arcname = os.path.basename(os.path.normpath(directory))
                tar.add(name=directory, arcname=arcname, exclude=exclude_fn)
                tar.close()
            else:
                # Tar all the files together
                for f in files:
                    tar.add(name=f, arcname=os.path.basename(f), exclude=exclude_fn)
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
                dct['atoms'] = atoms2dict(dct['atoms'], plain_arrays=True)

            # Serialise the data and send it to remote
            data_string = json.dumps(data_out)
            communicate_via_ssh(args.remote, sys_args, tty=True, data_out=data_string)
        else:
            # Write atoms to the database
            box, token = init_backend(args.database, user, readonly)
            atoms_list = [dct['atoms'] for dct in parsed]
            if args.store:
                result = box.insert(token, atoms_list, kvp)
            else:
                result = box.update(token, atoms_list, args.upsert, args.replace)
            print_result(result, parsed, aux_files, args.database)

    elif args.add_keys:
        if ssh and local:
            communicate_via_ssh(args.remote, sys_args, tty=True)
        else:
            box, token = init_backend(args.database, user, readonly)
            result = box.add_keys(token, query, kvp)
            print(result.msg)

    elif args.remove_keys:
        if ssh and local:
            communicate_via_ssh(args.remote, sys_args, tty=True)
        else:
            box, token = init_backend(args.database, user, readonly)
            result = box.remove_keys(token, query, remove_keys)
            print(result.msg)

    elif args.count and ssh and local:
        communicate_via_ssh(args.remote, sys_args, tty=True)

    # Count selected configurations
    elif args.count:
        box, token = init_backend(args.database, user, readonly)

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
        communicate_via_ssh(args.remote, sys_args, tty=True)

    

    elif ssh and local:
        communicate_via_ssh(args.remote, sys_args, tty=True)

    elif args.ids:
        box, token = init_backend(args.database, user, readonly)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        for atoms in atoms_it:
            print(atoms.info['uid'])

    # Show the database
    elif args.show:
        box, token = init_backend(args.database, user, readonly)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)

        if keys != '++':
            truncate = False
        else:
            truncate = True
        print_rows(atoms_it, border=args.pretty, 
            truncate=truncate, show_keys=keys, omit_keys=omit_keys)

    # List all available databases
    elif (args.list or not args.database) and ssh and local:
        communicate_via_ssh(args.remote, sys_args, tty=True)
        return

    elif args.list or not args.database:
        box, token = init_backend(args.database, user, readonly)

        dbs = box.list(token)
        if user:
            username = user
        else:
            username = 'Local User'
        if dbs:
            print(('Hello, {}. Databases you have access to:').format(username))
            for db in dbs:
                print('   {}'.format(db))
        else:
            print(('Hello, {}. You don\'t have access to any databases.').format(username))
        return

    # Print info about keys
    else:
        box, token = init_backend(args.database, user, readonly)
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=args.sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        print_keys_table(atoms_it, show_keys=keys, omit_keys=omit_keys)

