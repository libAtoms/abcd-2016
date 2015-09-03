from __future__ import print_function
import argparse
import getpass
import os
import StringIO
import sys
import tarfile
from ase.atoms import Atoms
from ase.db.core import convert_str_to_float_or_str
from ase.io import read as ase_read
from ase.io import write as ase_write
from authentication import Credentials
from base64 import b64encode, b64decode
from config import read_config_file, create_config_file, config_file_exists
from query import translate
from random import randint
from results import UpdateResult, InsertResult
from structurebox import StructureBox
from table import print_keys_table, print_rows, print_long_row

description = ''

examples = '''
    abcd --remote abcd@gc121mac1 db1.db --show   (display the database)
    abcd --remote abcd@gc121mac1 db1.db   (display information about available keys)
    abcd abcd@gc121mac1:db1.db \'energy<0.6 id>4 id<20 id!=10,11,12 elements~C elements~H,F,Cl\'   (querying; remote can be specified using a colon before the database name)
    abcd abcd@gc121mac1:db1.db --extract-original-files --path-prefix extracted/   (extract original files to the extracted/ folder)
    abcd abcd@gc121mac1:db1.db --write-to-file extr.xyz   (write selected configurations to the file extr.xyz)
    abcd db1.db \'energy>0.7\' --count   (count number of selected rows)
    abcd db1.db \'energy>0.8\' --remove   (remove selected configurations)
    abcd db1.db --store conf1.xyz conf2.xyz info.txt   (store original files in the database)
    abcd db1.db --store configs/   (store the whole directory in the database)
    abcd db1.db --omit-keys 'user,id' --show  (show the database, but omit keys user and id)
'''

def main():
    sys_args = sys.argv[1:]
    if isinstance(sys_args, str):
        sys_args = sys_args.split(' ')

    if not config_file_exists():
        create_config_file()

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

    parser = argparse.ArgumentParser(usage = 'abcd [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Examples: ' + examples,
                        formatter_class=argparse.RawTextHelpFormatter)

    # Display usage if no arguments are supplied
    if len(sys_args) == 0:
        parser.print_usage()

    add = parser.add_argument
    add('database', nargs='?', help = 'Specify the database')
    add('query', nargs = '*', default = '', help = 'Query')
    add('-U', '--user', nargs='?', metavar='USER', default=None, const=[], help='User. Leave blank to input via stdin')
    add('-P', '--password', nargs='?', metavar='PASSWD', default=None, const=[], help='Password. Leave blank to input via stdin')
    add('-v', '--verbose', action='store_true', default=False)
    add('-q', '--quiet', action='store_true', default=False)
    add('--remote', help = 'Specify the remote')
    add('-l', '--list', action = 'store_true', 
        help = 'Lists all the databases you have access to')
    add('-o', '--show', action='store_true', help='Show the database')
    add('-g', '--long', action='store_true', help='Show more informaion about one selected configuration')
    add('--pretty', action='store_true', default=True, help='Use pretty tables')
    add('--no-pretty', action='store_false', dest='pretty', help='Don\'t use pretty tables')
    add('-m', '--limit', type=int, default=0, metavar='N',
        help='Show only first N rows. Use 0 to show all (default).')
    add('-z', '--sort', metavar='COL', default='',
        help='Specify the column to sort the rows by. Default is increasing order \n(change it using --reverse)')
    add('-i', '--reverse', action='store_true', default=False, help='Reverses the sorting order')
    add('-c', '--count', action='store_true',
        help='Count number of selected rows.')
    add('-k', '--show-keys', metavar='K1,K2,...', default='', help='Select only specified keys. "+" for all.')
    add('-n', '--omit-keys', metavar='K1,K2,...', default='', help='Don\'t select these keys')
    add('-t', '--add-keys', metavar='K1=V1,...', help='Add key-value pairs')
    add('--remove-keys', metavar='K1,K2,...', help='Remove keys')
    add('--remove', action='store_true',
        help='Remove selected rows.')
    add('-s', '--store', metavar='', nargs='+', help='Store a directory / list of files')
    add('-u', '--update', metavar='', nargs='+', help='Update the databse with a directory / list of files')
    add('--replace', action='store_true', default=False, 
        help='Replace configurations with the same uid when using --update')
    add('--no-replace', action='store_false', dest='replace', 
        help='Don\'t replace configurations with the same uid when using --update')
    add('--upsert', action='store_true', default=False, 
        help='Insert configurations which are not yet in the database when using --update')
    add('--no-upsert', action='store_false', dest='upsert', 
        help='Don\'t insert configurations which are not yet in the database when using --update')
    add('-x', '--extract-original-files', action='store_true',
        help='Extract original files stored with --store')
    add('--untar', action='store_true', default=True,
        help='Automatically untar files extracted with --extract-files')
    add('--no-untar', action='store_false', dest='untar',
        help='Don\'t automatically untar files extracted with --extract-files')
    add('-p', '--path-prefix', metavar='PREFIX', default='.', help='Path prefix for extracted files')
    add('-w', '--write-to-file', metavar='FILE',
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

    # Calculate the verbosity
    # Verbosity can be either 0, 1 or 2
    verbosity = 1 - args.quiet + args.verbose

    try:
        run(args, sys_args, verbosity)
    except Exception as x:
        if verbosity < 2:
            print('{0}: {1}'.format(x.__class__.__name__, x), file=sys.stderr)
            sys.exit(1)
        else:
            raise


def to_stderr(*args):
    '''Prints to stderr'''
    if args and any(not arg.isspace() for arg in args):
        print(*(arg.rstrip('\n') for arg in args), file=sys.stderr)


def untar_file(fileobj, path_prefix):
    try:
        tar = tarfile.open(fileobj=fileobj, mode='r')
        members = tar.getmembers()
        no_files = len(members)
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
            untar_file(f, path_prefix)
        os.remove(tarball)


def print_result(result, multiconfig_files, database):

    if isinstance(result, UpdateResult):
        n_succ = len(result.updated_ids) + len(result.upserted_ids) + len(result.replaced_ids)

        # Print "10 configurations were updated:"
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

        # Print "10 configurations were inserted:"
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
    if n_succ and multiconfig_files:
        print('The following files were not included as original files:')
        for f in multiconfig_files:
            print('  ', f)


def run(args, sys_args, verbosity):

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0 and args and any(not arg.isspace() for arg in args):
            print(*(arg.rstrip('\n') for arg in args))

    # Get the query
    query = translate(args.query)

    # Plus resets args.omit_keys
    if args.show_keys == '+':
        args.show_keys = ''
        args.omit_keys = ''

    # Decide which keys to show
    keys = args.show_keys.split(',')
    if '' in keys:
        keys.remove('')
    
    omit_keys = args.omit_keys.split(',')
    if '' in omit_keys:
        omit_keys.remove('')

    sort = args.sort.split(',')
    if '' in sort:
        sort.remove('')

    # Get kvp
    kvp = {}
    if args.add_keys:
        for pair in args.add_keys.split(','):
            k, sep, v = pair.partition('=')
            kvp[k] = convert_str_to_float_or_str(v)

    # Get keys to be removed
    remove_keys = []
    if args.remove_keys:
        for key in args.remove_keys.split(','):
            remove_keys.append(key)


    #
    #
    # Backend initialisation and authentication
    cfg = read_config_file()
    backend_module = cfg.get('abcd', 'backend_module')
    backend_name = cfg.get('abcd', 'backend_name')

    # Quit if no backend was specified
    if not backend_module or not backend_name:
        print('  Please specify the backend in ~/.abcd_config')
        sys.exit()

    # Import the backend
    Backend = getattr(__import__(backend_module, fromlist=[backend_name]), backend_name)

    # Initialise the backend
    box = StructureBox(Backend(database=args.database, remote=args.remote))

    # Get the username and password
    if args.user == []:
        user = raw_input('User: ')
    else:
        user = args.user

    if args.password == []:
        password = getpass.getpass()
    else:
        password = args.password

    # Authenticate
    token = box.authenticate(Credentials(user))
    #
    #
    #


    # Remove entries from a database
    if args.remove:
        result = box.remove(token, query, just_one=False)
        print(result.msg)

    # Extract a configuration from the database and write it
    # to the specified file.
    elif args.write_to_file:
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

        nrows = 0
        list_of_atoms = []
        omit = omit_keys + ['original_files']
        for atoms in box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
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
            write_atoms_locally(list_of_atoms, name, format, args.path_prefix)
            files_written = 1
        else:
            # Write extracted configurations into separate files
            for i, atoms in enumerate(list_of_atoms):
                name = filename % i + '.' + display_format
                write_atoms_locally(atoms, name, format, args.path_prefix)
                files_written += 1

        out('  Writing {} file(s) to {}/'.format(files_written, args.path_prefix))

    # Extract original file(s) from the database and write them
    # to the directory specified by the --path-prefix argument 
    # (current directory by default), or print the file
    # to stdout.
    elif args.extract_original_files:
        # Extract original file contents from the atoms
        names = []
        unique_ids = []
        original_files =[]
        skipped_configs = []
        nat = 0
        for atoms in box.find(auth_token=token, filter=query, 
                        sort=sort, reverse=args.reverse,
                        limit=args.limit,
                        keys=['original_files', 'uid']):
            nat += 1

            # Find the original file contents
            contents = ''
            if 'original_files' in atoms.info:
                contents = atoms.info['original_files']
            elif 'original_files' in atoms.arrays:
                contents = atoms.arrays['original_files']
            elif 'original_file_contents' in atoms.info:
                contents = atoms.info['original_file_contents']
            elif 'original_file_contents' in atoms.arrays:
                contents = atoms.arrays['original_file_contents']
            else:
                skipped_configs.append(nat)
                continue

            name = atoms.get_chemical_formula()
            if len(name) > 15:
                name = str[:15]
            names.append(name)

            # The Atoms object should have a uid, but if it doesn't
            # then use uid='0'.
            if 'uid' in atoms.info and atoms.info['uid'] is not None:
                unique_ids.append(atoms.info['uid'])
            else:
                unique_ids.append('0')
            original_files.append(contents)

        # Mangle the names
        for i, name in enumerate(names):
            names[i] += '-' + str(unique_ids[i])[-15:]

        extracted_paths = []

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
        if extracted_paths:
            if args.untar:
                untar_and_delete(extracted_paths, args.path_prefix)
                msg += '  Files were untarred to {}/'.format(args.path_prefix)
            else:
                msg += '  Files were written to {}/'.format(args.path_prefix)
        out(msg)

    elif (args.store or args.update):
        if args.store:
            to_store = args.store
        else:
            to_store = args.update

        def parse(f):
            try:
                return ase_read(f, index=slice(0, None, 1))
            except:
                return None

        atoms_to_store = []
        multiconfig_files = []

        # Clasify each argument as either file or directory
        auxilary_files = []
        parsable_files = []
        dirs = []
        for f in to_store:
            if os.path.isfile(f):
                atoms = parse(f)
                if atoms is not None:
                    parsable_files.append({'atoms': atoms, 'path': f})
                else:
                    auxilary_files.append({'path': f, 'name': os.path.basename(f)})
            elif os.path.isdir(f):
                dirs.append(f)
            else:
                raise IOError('No such file or directory: "{}"'.format(f))

        def create_tarball(aux_files, atoms, atoms_fname, short_fnames=False):
            '''If short_fnames is True, only last portion of the filename is used.
                Returns b64encoded tarball (or an empty string)'''
            c = StringIO.StringIO()
            tar = tarfile.open(fileobj=c, mode='w')

            # Add auxilary files
            for aux_f in aux_files:
                arcname = aux_f['name']
                tar.add(name=aux_f['path'], arcname=arcname)

            # Add the file containing the original configuration,
            # but only if it isn't a multi-config file.
            arcname = os.path.basename(atoms_fname) if short_fnames else atoms_fname
            if len(atoms) == 1:
                tar.add(name=atoms_fname, arcname=arcname)
            else:
                multiconfig_files.append(arcname)

            ret = ''
            if tar.getmembers():
                ret = b64encode(c.getvalue())

            tar.close()
            return ret

        def walk(tree, atoms_to_store, aux=[]):
            for parsed_dct in tree['parsable']:
                atoms = parsed_dct['atoms']
                atoms_fname = parsed_dct['path']
                aux_files = aux + tree['auxilary']

                tar = create_tarball(aux_files, atoms, atoms_fname)

                # Attach the tar to the Atoms objects and add the Atoms objects to
                # atoms_to_store.
                for ats in atoms:
                    if tar:
                        ats.info['original_files'] = tar
                    atoms_to_store.append(ats)

            for subdir_name, subdir in tree['subdirs'].iteritems():
                walk(subdir, atoms_to_store, aux + tree['auxilary'])

        # Files were specified on the command line
        if parsable_files:
            # Iterate over parsed files
            for parsed_dct in parsable_files:
                atoms = parsed_dct['atoms']
                atoms_fname = parsed_dct['path']

                tar = create_tarball(auxilary_files, atoms, atoms_fname, short_fnames=True)

                for ats in atoms:
                    if tar:
                        ats.info['original_files'] = tar
                    atoms_to_store.append(ats)

        # At least one directory was specified on the command line.
        for d in dirs:
            # Convert directories to a tree

            d = d.rstrip(os.sep)
            parent_dir, dirname = os.path.split(d)

            # Change the directory to parent_dir so that all the names are relative to it
            if parent_dir:
                os.chdir(parent_dir)

            # If any additional auxilary files were specified, treat them as being in
            # the directory "dirname".
            additional_aux = [{'path': dct['path'], 'name': os.path.join(dirname, dct['name'])} for dct in auxilary_files]
            tree = {dirname: {'subdirs': {}, 'parsable': [], 'auxilary': additional_aux}}

            for root, dirs, files in os.walk(dirname):
                folders = list(root.split(os.sep))
                if '' in folders:
                    folders.remove('')

                current = tree
                for i, folder in enumerate(folders):
                    if i == 0:
                        current = current[folder]
                    else:
                        current = current['subdirs'][folder]
                for subdir in dirs:
                    current['subdirs'][subdir] = {'subdirs': {}, 'parsable': [], 'auxilary': []}

                for f in files:
                    fname = os.path.join(root, f)
                    atoms = parse(fname)
                    if atoms is None:
                        current['auxilary'].append({'path': fname, 'name': fname})
                    else:
                        current['parsable'].append({'atoms': atoms, 'path': fname})

            # Now walk the tree to find all parsed files
            walk(tree[dirname], atoms_to_store)

        # Chech if the atoms we are about to insert/update have a uid.
        # If not, attach one.
        for atoms in atoms_to_store:
            if not 'uid' in atoms.info or atoms.info['uid'] is None:
                atoms.info['uid'] = '%x' % randint(16**14, 16**15 - 1)

        # Store/update parsed atoms
        if args.store:
            result = box.insert(token, atoms_to_store)
        else:
            result = box.update(token, atoms_to_store, args.upsert, args.replace)
        print_result(result, multiconfig_files, args.database)

    elif args.add_keys:
        result = box.add_keys(token, query, kvp)
        print(result.msg)

    elif args.remove_keys:
        result = box.remove_keys(token, query, remove_keys)
        print(result.msg)

    # Count selected configurations
    elif args.count:
        if args.limit == 0:
            lim = 0
        else:
            lim = args.limit + 1
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
                            limit=lim, keys=keys, omit_keys=omit_keys)
        count = atoms_it.count()
        if args.limit != 0 and count > args.limit:
            count = '{}+'.format(count-1)
        else:
            count = str(count)
        print('Found:', count)

    elif args.ids:
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        for atoms in atoms_it:
            uid = atoms.info.get('uid')
            print('  ' + uid)

    # Show the database
    elif args.show:
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        print_rows(atoms_it, border=args.pretty, 
            truncate=args.pretty, show_keys=keys, omit_keys=omit_keys)

    elif args.long:
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        try:
            atoms = next(atoms_it)
        except StopIteration:
            to_stderr('No matches')
            return

        try:
            next(atoms_it)
            to_stderr('\nWarning: more than one matches. Showing only one configuration.')
        except StopIteration:
            pass

        print_long_row(atoms)

    elif args.list or not args.database:
        dbs = box.list(token)
        if dbs:
            print('Hello. Databases you have access to:')
            for db in dbs:
                print('   {}'.format(db))
        else:
            print('Hello. You don\'t have access to any databases.')

    # Print info about keys
    else:
        atoms_it = box.find(auth_token=token, filter=query, 
                            sort=sort, reverse=args.reverse,
                            limit=args.limit, keys=keys, omit_keys=omit_keys)
        print_keys_table(atoms_it, border=args.pretty, 
            truncate=args.pretty, show_keys=keys, omit_keys=omit_keys)
