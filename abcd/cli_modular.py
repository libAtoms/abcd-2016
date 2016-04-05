"""
abcd commandline client

"""

from __future__ import print_function

import argparse
import getpass
import os
import io
import shlex
import sys
import tarfile
import time

from abcd import Direction
from ase.atoms import Atoms
from ase.db.core import convert_str_to_float_or_str
from ase.io import read as ase_read
from ase.io import write as ase_write
from .authentication import Credentials
from base64 import b64encode, b64decode
from .config import ConfigFile
from .query import translate
from random import randint
from .results import UpdateResult, InsertResult
from .structurebox import StructureBox
from .table import print_keys_table, print_rows, print_long_row
from abcd.util.atoms import atoms_to_files

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
    abcd db1.db --keys 'user,id' --omit-keys --show  (show the database, but omit keys user and id)
    abcd db1.db --sort 'energy:A,age:D' --show  (sort by energy (ascending) and age (descending))
'''

def main():
    sys_args = sys.argv[1:]
    if isinstance(sys_args, str):
        sys_args = sys_args.split(' ')

    config_file = ConfigFile('cli')

    if not config_file.exists():
        defaults = {'abcd': {
            'opts': '',
            'backend_module': '',
            'backend_name': ''}}
        config_file.initialise(defaults)

    # Load the options from the config file. Push them to the front of the list
    # so they will be overwritten on the command line.
    cfg_options = config_file.get('abcd', 'opts')
    # parse string as commadline options
    new_args = shlex.split(cfg_options)
    # Stick them at the front
    # TODO: will not work with subcommands
    sys_args = new_args + sys_args


    # Construct the argument parser as a series of subcommands.
    # Just one parser at the top level
    parser = argparse.ArgumentParser(
        description="abcd - the atom based configuration database. ",
        epilog="See the help of individual commands for complete usage info.")

    # Each subcommand is constructued of predefined option sets and options
    # specific to that command.

    class DecreaseAction(argparse.Action):
        """Decrease the destination by 1 for each call."""

        def __call__(self, parser, namespace, values, option_string=None):
            """Decrease destination by one."""
            previous_value = getattr(namespace, self.dest)
            setattr(namespace, self.dest, previous_value - 1)

    # The database is always the first argument, if it is required,
    # Comes before and commands or options.
    parser.add_argument('database', nargs='?',
                        help="The database to work on. Accepts database name, "
                             "full path or bookmark.")

    # General nosiness
    p_verbosity = argparse.ArgumentParser(add_help=False)
    p_verbosity.add_argument("-v", "--verbose", action="count", default=0,
                             dest="verbosity",
                             help="Increase verbosity. Specify the option "
                                  "more times for more debugging "
                                  "information. Cancels '--quiet'.")
    p_verbosity.add_argument("-q", "--quiet", action=DecreaseAction, nargs=0,
                             dest="verbosity",
                             help="Decrease verbosity. Specify the option "
                                  "more times for less output. Cancels "
                                  "'--verbose'.")

    # Query options

    # Credentials
    p_credentials = argparse.ArgumentParser(add_help=False)
    p_credentials.add_argument('-u', '--user', nargs='?', const='',
                               help="Username used to log in to a database.")

    # Each command enacts a different action that will correspond to a method
    # of Abcd.
    subparsers = parser.add_subparsers(title="Commands", dest='command')

    p_store = subparsers.add_parser("store", parents=[p_verbosity, p_credentials],
                                    help="Store new configurations in the "
                                         "database.")
    p_store.add_argument('filename', nargs='+',
                         help="Names of files or directories to process and "
                              "store in the database.")
    p_store.add_argument('--update', action='store_true',
                         help="Perform an update of the configurations, "
                              "rather than create new ones.")

    p_extract = subparsers.add_parser("extract")

    # TODO: switch to new argument system
    #print(parser.parse_args())

    parser = argparse.ArgumentParser(usage = 'abcd [db-name] [selection] [options]',
                        description = description,
                        epilog = 'Examples: ' + examples,
                        formatter_class=argparse.RawTextHelpFormatter)

    # Display usage if no arguments are supplied
    if len(sys_args) == 0:
        parser.print_usage()

    # Actions:



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
    add('-z', '--sort', metavar='COL1:[A/D],COL2[A/D]...', default='',
        help='Specify columns to sort the rows by (default direction is ascending). Multicolumn sorting might not be supported by all backends.')
    add('-c', '--count', action='store_true',
        help='Count number of selected rows.')
    add('-k', '--keys', metavar='K1,K2,...', help='Select only specified keys. "+" for all. See also --omit-keys.')
    add('-n', '--omit-keys', action='store_true', help='Omit keys specified with --keys argument')
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
        with open(tarball, 'rb') as f:
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

class Abcd(object):
    """API interface to the functionality of the commandline.

    Instance with a database identifier and it will take care of
    initialisation and provide methods to work with the selected database.
    For a more low level interface, look at StructureBox.
    """
    def __init__(self, database, **kwargs):
        """
        Possible kwargs:
        remote : remote server to use
        user : username, leave as empty string to ask for username
        """
        # Add all the general options and initialisation here.

        # Figure out the database
        # TODO: multiple plugins and bookmarks; not cfg file
        # FIXME: No database case
        if ':' in database:
            remote, database = database.split(':')
            if 'remote' in kwargs and kwargs['remote'] is not None and kwargs['remote'] != remote:
                print('Error: Remote specified twice: "{}" and "{}"'.format(
                    remote, kwargs['remote']), file=sys.stderr)
                sys.exit()
            self.remote = remote
            self.database = database
        else:
            self.database = database
            self.remote = None

        # Backend initialisation and authentication
        cfg = ConfigFile('cli')
        backend_module = cfg.get('abcd', 'backend_module')
        backend_name = cfg.get('abcd', 'backend_name')

        # Quit if no backend was specified
        if not backend_module or not backend_name:
            print('  Please specify the backend in {}'.format(cfg.path))
            sys.exit()

        # Import the backend
        Backend = getattr(__import__(backend_module, fromlist=[backend_name]),
                          backend_name)

        # Initialise the backend
        # TODO: rename 'box'
        self.box = StructureBox(Backend(database=self.database,
                                        remote=self.remote))

        # Get the username and password
        if 'user' in kwargs and kwargs['user'] == '':
            try:
                # PY2 compat
                self.user = raw_input('User: ')
            except NameError:
                self.user = input('User: ')
        elif 'user' in kwargs:
            self.user = kwargs['user']
        else:
            self.user = None

        if 'password' in kwargs and kwargs['password'] =='':
            self.password = getpass.getpass()
        elif 'password' in kwargs:
            self.password = kwargs['password']
        else:
            self.password = None

        # Authenticate
        self.token = self.box.authenticate(Credentials(self.user))
        # TODO: actual authentication

        print(self.box)

    def remove(self, query, just_one=False):
        """Remove entries from the database. """
        # Remove entries from a database
        result = self.box.remove(self.token, query, just_one=just_one)
        return result

    def find(self, filter, sort=None, limit=0, keys=None,
             omit_keys=False):
        if sort is None:
            sort = {}
        return self.box.find(auth_token=self.token, filter=filter, sort=sort,
                             limit=limit, keys=keys, omit_keys=omit_keys)


    def write_to_file(self, filter, filename='out.xyz', format=None, sort=None,
                      limit=0, keys=None, omit_keys=False):
        """
        Find the configurations given the query options, write the extracted
        configurations to a file.
        """
        atoms = list(self.box.find(auth_token=self.token, filter=filter,
                                   sort=sort, limit=limit, keys=keys,
                                   omit_keys=omit_keys))

        return atoms_to_files(atoms, filename=filename, format=format)

    def extract_original_files(self):
        pass

    def store(self):
        pass

    def add_keys(self, filter, kvp):
        """Add the key=value pairs to the filtered configurations."""
        result = self.box.add_keys(auth_token=self.token, filter=filter, kvp=kvp)

    def remove_keys(self, filter, keys):
        """Remove keys from filtered configurations."""
        result = self.box.remove_keys(auth_token=self.token, filter=filter, keys=keys)
        return result

    def count(self):
        pass

    def ids(self):
        pass

    def show(self):
        pass

    def long(self):
        pass

    def list(self):
        pass



def run(args, sys_args, verbosity):

    def out(*args):
        '''Prints information in accordance to verbosity'''
        if verbosity > 0 and args and any(not arg.isspace() for arg in args):
            print(*(arg.rstrip('\n') for arg in args))

    # Get the query
    query = translate(args.query)

    if args.omit_keys and args.keys is None:
        print('Error: No keys to omit specified. Use --keys')
        sys.exit()
    omit_keys = args.omit_keys

    if args.keys is None or args.keys == '+':
        keys = None
    else:
        keys = args.keys.split(',')
        keys = [k for k in keys if k not in ('', ' ')]

    sort_list = args.sort.split(',')
    sort_list = [s for s in sort_list if s not in (None, '', ' ')]
    sort = {}
    for s in sort_list:
        if ':' in s:
            key, direction = s.split(':')
            if direction in ('A', 'a', 'ascending', 'Ascending', 'ASCENDING'):
                direction = Direction.ASCENDING
            elif direction in ('D', 'd', 'descending', 'Descending', 'DESCENDING'):
                direction = Direction.DESCENDING
        else:
            key = s
            direction = Direction.ASCENDING
        sort[key] = direction

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
    remove_keys = [a for a in remove_keys if a not in (None, '', ' ')]

    # 'Connect' to the database
    my_abcd = Abcd(database=args.database, remote=args.remote,
                   user=args.user, password=args.password)

    #
    # Do things with the database...
    #

    # Delete
    if args.remove:
        print(my_abcd.remove(query).msg)

    # Extract a configuration from the database and write it
    # to the specified file.
    elif args.write_to_file:

        # Make sure 'original_files' is omitted
        omit = omit_keys
        if keys is not None and omit:
            keys.append('original_files')
        elif keys is not None and 'original_files' in keys:
            keys.remove('original_files')
        elif keys is None and omit:
            # All keys will be omitted
            pass
        else:
            keys = ['original_files']
            omit = True

        # filename in the write to file argument
        nfiles, nconfigs = my_abcd.write_to_file(
            query, args.write_to_file, format=None, sort=sort,
            limit=args.limit, keys=keys,  omit_keys=omit)

        out('  Wrote {} configs in {} file(s)'.format(nconfigs, nfiles))

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
                        sort=sort, limit=args.limit,
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

            with open(path, 'wb') as original_file:
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
            c = io.BytesIO()
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
                        ats.info['original_files'] = str(tar)
                    atoms_to_store.append(ats)

            for subdir_name, subdir in tree['subdirs'].items():
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
                        ats.info['original_files'] = str(tar)
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

        for atoms in atoms_to_store:
            # Check if the configuration has a uid.
            # If not, attach one.
            if not 'uid' in atoms.info or atoms.info['uid'] is None:
                atoms.info['uid'] = '%x' % randint(16**14, 16**15 - 1)

            # Add c_time, formula and n_atoms
            if not 'c_time' in atoms.info:
                atoms.info['c_time'] = int(time.time())
            if not 'formula' in atoms.info:
                atoms.info['formula'] = atoms.get_chemical_formula()
            if not 'n_atoms' in atoms.info:
                atoms.info['n_atoms'] = len(atoms.numbers)

        # Store/update parsed atoms
        if args.store:
            result = box.insert(token, atoms_to_store)
        else:
            result = box.update(token, atoms_to_store, args.upsert, args.replace)
        print_result(result, multiconfig_files, args.database)

    elif args.add_keys:
        result = my_abcd.add_keys(query, kvp)
        print(result.msg)

    elif args.remove_keys:
        result = my_abcd.remove_keys(query, remove_keys)
        print(result.msg)

    # Count selected configurations
    elif args.count:
        # Zero is no limit, but count at least as many as limit
        if args.limit == 0:
            lim = 0
        else:
            lim = args.limit + 1
        atoms_it = my_abcd.find(filter=query,
                                sort=sort, limit=lim, keys=keys,
                                omit_keys=omit_keys)
        count = atoms_it.count()
        if args.limit != 0 and count > args.limit:
            count = '{}+'.format(count-1)
        else:
            count = str(count)
        print('Found:', count)

    elif args.ids:
        atoms_it = my_abcd.find(filter=query,
                                sort=sort, limit=args.limit,
                                keys=keys, omit_keys=omit_keys)
        for atoms in atoms_it:
            uid = atoms.info.get('uid')
            print('  ' + uid)

    # Show the database
    elif args.show:
        atoms_it = my_abcd.find(filter=query,
                                sort=sort, limit=args.limit,
                                keys=keys, omit_keys=omit_keys)
        print_rows(atoms_it, border=args.pretty,
                   truncate=args.pretty, show_keys=keys,
                   omit_keys=omit_keys)

    elif args.long:
        atoms_it = my_abcd.find(filter=query,
                                sort=sort, limit=args.limit,
                                keys=keys, omit_keys=omit_keys)
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
        # TODO: backends list each of their databases
        dbs = my_abcd.box.list(my_abcd.token)
        if dbs:
            print('Hello. Databases you have access to:')
            for db in dbs:
                print('   {}'.format(db))
        else:
            print('Hello. You don\'t have access to any databases.')

    # Print info about keys
    else:
        atoms_it = my_abcd.find(filter=query,
                                sort=sort, limit=args.limit, keys=keys,
                                omit_keys=omit_keys)
        print_keys_table(atoms_it, border=args.pretty,
            truncate=args.pretty, show_keys=keys, omit_keys=omit_keys)
