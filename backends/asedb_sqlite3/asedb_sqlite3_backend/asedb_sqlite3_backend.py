__author__ = 'Patrick Szmucer'

import glob
import json
import numpy as np
import os
import re
import abcd.backend
import abcd.results as results
from abcd.authentication import AuthenticationError
from abcd.backend import Backend, ReadError, WriteError
from abcd.query import QueryError, translate
from abcd.util import get_info_and_arrays, atoms2dict, dict2atoms, filter_keys
from ase.atoms import Atoms
from ase.calculators.calculator import all_properties
from ase.calculators.singlepoint import SinglePointCalculator
from ase.db import connect
from ase.utils import plural
from base64 import b64encode

from .mongodb2asedb import translate_query
from random import randint
from .remote import communicate_with_remote
from .util import get_dbs_path, reserved_usernames


def row2atoms(row, keys, omit_keys):
    """
    keys: keys to show. None for all
    omit_keys: if true, all keys not in "keys" will be shown
    """
    atoms = row.toatoms()

    # Add additional info
    if row._keys:
        atoms.info.update(row.key_value_pairs)

    data = row.get('data')
    if data:
        for (key, value) in list(data.items()):
            key = str(key) # avoid unicode strings
            value = np.array(value)
            if value.dtype.kind == 'U':
                value = value.astype(str)
            try:
                atoms.new_array(key, value)
            except (TypeError, ValueError):
                atoms.info[key] = value

    # unique_id is added automatically by ASEdb, we don't need it
    atoms.info.pop('unique_id', None)

    filtered_keys = filter_keys(list(atoms.info.keys()), keys, omit_keys)
    atoms.info = {k: v for k, v in atoms.info.items() if k in filtered_keys}
    return atoms


class ASEdbSQlite3Backend(Backend):

    class Cursor(abcd.backend.Cursor):
        def __init__(self, iterator):
            self.iterator = iterator

        def __next__(self):
            return next(self.iterator)

        def count(self):
            n = 0
            for a in self.iterator:
                n += 1
            return n

    def require_database(func):
        '''When a function is decorated with this, an error will be thrown if
            the connection to a database is not open.'''
        def func_wrapper(*args, **kwargs):
            if args[0].connection is None:
                raise ReadError("No database is specified")
            else:
                return func(*args, **kwargs)
        return func_wrapper

    def read_only(func):
        def func_wrapper(*args, **kwargs):
            if args[0].readonly:
                raise WriteError('No write access')
            else:
                return func(*args, **kwargs)
        return func_wrapper

    def __init__(self, database=None, user=None, password=None, remote=None):
        if user == 'all':
            raise RuntimeError('Invalid username: '.format('all'))
        self.user = user
        self.dbs_path = get_dbs_path()
        self.connection = None
        self.root_dir = None
        self.remote = remote
        self.readonly = True

        # Get the user. If the script is running locally, we have access
        # to all databases.
        if self.user:
            home = self.user
        else:
            home = 'all'

        # root_dir is the directory in which user's databases are stored
        self.root_dir = os.path.join(self.dbs_path, home)

        # Make sure the database name is safe and connect to it
        if database == '':
            self.database = None
        else:
            self.database = database
        if self.database:
            self.database = os.path.basename(self.database)
            if self.database.endswith('.db'):
                self.database = self.database[:-3]
            if not re.match(r'^[A-Za-z0-9_]+$', self.database):
                raise RuntimeError('The database name can only contain alphanumeric characters and underscores.')
            self.database = self.database + '.db'
            self.connect_to_database()

        # Check if the $databases/all directory exists.
        all_path = os.path.join(self.dbs_path, 'all')
        if not os.path.isdir(all_path):
            cmd = 'python asedb_sqlite3_backend.py --setup'
            raise RuntimeError('{} does not exist. Run "{}" first'.format(all_path, cmd))

        super(ASEdbSQlite3Backend, self).__init__()

    def _select(self, query, sort={}, limit=0):
        query = translate_query(query)
        if sort == {}:
            sort = 'id'
            reverse = False
        else:
            # This backend does not support multicolumn sorting.
            # Only sort by first column.
            sort, direction = next(iter(sort.items()))
            if direction == abcd.Direction.ASCENDING:
                reverse = False
            else:
                reverse = True
        rows = []
        ids = []
        for q in query:
            rows_iter = self.connection.select(q, sort=sort, limit=limit)
            for row in rows_iter:
                if 'uid' not in row.key_value_pairs:
                    rows.append(row)
                elif row.key_value_pairs['uid'] not in ids:
                    rows.append(row)
                    ids.append(row.key_value_pairs['uid'])

        # Because a union was created, items are not in a sorted order
        # anymore.
        if sort:
            rows.sort(key=lambda x: getattr(x, sort), reverse=reverse)

        if limit != 0 and len(rows) > limit:
            return rows[:limit]
        else:
            return rows

    def list(self, auth_token):
        if self.remote:
            dbs = communicate_with_remote(self.remote, 'list')
        else:
            dbs_write = glob.glob(os.path.join(self.root_dir, '*.db'))
            dbs_read = glob.glob(os.path.join(self.root_dir + '_readonly', '*.db'))
            dbs = dbs_write + [db + ' (readonly)' for db in dbs_read]
        return [os.path.basename(db) for db in dbs]

    def authenticate(self, credentials):
        if credentials.username in reserved_usernames:
            raise AuthenticationError('Username "{}" is reserved'.format(credentials.username))
        return credentials.username

    def connect_to_database(self):
        '''
        Connnects to a database with given name. If it doesn't
        exist, a new one is created. The method first looks in the
        "write" folder, and then in the "readonly" folder
        '''

        # Check if "readonly" and "write" directories exist
        if not os.path.isdir(self.root_dir):
            raise WriteError('{} does not exist. Create it.'.format(self.root_dir))
        if self.user and not os.path.isdir(self.root_dir + '_readonly'):
            raise WriteError('{} does not exist. Create it.'.format(self.root_dir + '_readonly'))

        write_db_path = os.path.join(self.root_dir, self.database)
        read_db_path = os.path.join(self.root_dir + '_readonly', self.database)

        if os.path.exists(write_db_path):
            write_exists = True
        else:
            write_exists = False

        if os.path.exists(read_db_path):
            read_exists = True
        else:
            read_exists = False

        if not read_exists and not write_exists:
            # No database with such name exists. Create one
            if self.user:
                new_db_name = '_' + self.user + '_' + self.database
            else:
                new_db_name = self.database
            new_db_path = os.path.join(self.dbs_path, 'all', new_db_name)
            self.connection = connect(new_db_path)

             # Create a symlink
            if self.user:
                user_db_path = os.path.join(self.root_dir, self.database)
                os.symlink(new_db_path, user_db_path)
            self.readonly = False

        elif (read_exists and write_exists) or (write_exists):
            # If two databsaes with the same name exist, connect to the "write" one
            self.connection = connect(write_db_path)
            self.readonly = False

        else:
            self.connection = connect(read_db_path)
            self.readonly = True

    def _preprocess(self, atoms):
        '''
        Load capitalised special key-value pairs into
        a calcuator.
        '''
        # The id key is not used
        atoms.info.pop('id', None)

        results = {}
        for key in atoms.info.keys():
            if key.lower() in all_properties:
                results[key.lower()] = atoms.info[key]
                del atoms.info[key]
        for key in atoms.arrays.keys():
            if key.lower() in all_properties:
                results[key.lower()] = atoms.arrays[key]
                del atoms.arrays[key]

        if results != {}:
            if atoms.calc is None:
                # Create a new calculator
                calculator = SinglePointCalculator(atoms, **results)
                atoms.set_calculator(calculator)
            else:
                # Use the existing calculator
                atoms.calc.results.update(results)

    def _insert_one_atoms(self, atoms):
        '''
        Inserts one Atoms object into the database, without checking if its
        uid is already present in the database. Returns a uid of the inserted
        object.
        '''
        if not 'uid' in atoms.info or atoms.info['uid'] is None:
            atoms.info['uid'] = '%x' % randint(16**14, 16**15 - 1)

        self._preprocess(atoms)
        info, arrays = get_info_and_arrays(atoms, plain_arrays=False)

        # Write it to the database
        self.connection.write(atoms=atoms, key_value_pairs=info, data=arrays)

        return atoms.info['uid']

    def _uid_exists(self, uid):
        '''
        Checks if a configuration with this uid already exists in the database.
        '''
        query = 'uid={}'.format(uid)
        rows_it = self.connection.select(query, limit=1)
        if sum(1 for _ in rows_it) != 0:
            return True
        else:
            return False

    @require_database
    @read_only
    def insert(self, auth_token, atoms_list):

        # Make sure we have a list
        if isinstance(atoms_list, Atoms):
            atoms_list = [atoms_list]

        if self.remote:
            dcts_list = [atoms2dict(atoms, True) for atoms in atoms_list]
            data = b64encode(json.dumps(dcts_list))
            cmd = 'insert {} {}'.format(self.database, data)
            return communicate_with_remote(self.remote, cmd)

        inserted_ids = []
        skipped_ids = []
        n_atoms = 0

        for atoms in atoms_list:
            n_atoms += 1

            # Check if it already exists in the database
            if 'uid' in atoms.info and atoms.info['uid'] is not None:
                uid = atoms.info['uid']
                exists = self._uid_exists(uid)
            else:
                uid = None
                exists = False

            # Check if this uid has already been "seen". If yes, skip it.
            if (uid is not None) and uid in (inserted_ids + skipped_ids):
                continue

            if not exists:
                # Insert it
                ins_uid = self._insert_one_atoms(atoms)
                inserted_ids.append(ins_uid)
            else:
                # It exists - skip it
                skipped_ids.append(uid)

        msg = 'Inserted {}/{} configurations.'.format(len(inserted_ids), n_atoms)
        return results.InsertResult(inserted_ids=inserted_ids, skipped_ids=skipped_ids, msg=msg)

    @require_database
    @read_only
    def update(self, auth_token, atoms_list, upsert, replace):
        '''Takes the Atoms object or a list of Atoms objects'''

        # Make sure it's a list
        if isinstance(atoms_list, Atoms):
            atoms_list = [atoms_list]

        if self.remote:
            dcts_list = [atoms2dict(atoms, True) for atoms in atoms_list]
            data = b64encode(json.dumps(dcts_list))
            cmd = 'update {} {}'.format(self.database, data)
            if upsert:
                cmd += ' --upsert'
            if replace:
                cmd += ' --replace'
            return communicate_with_remote(self.remote, cmd)

        def update_atoms_dct(d1, d2):
            # Update info and arrays
            if 'info' in d1 and 'info' in d2:
                d1['info'].update(d2['info'])
            if 'arrays' in d1 and 'arrays' in d2:
                d1['arrays'].update(d2['arrays'])
            # Update the rest
            for k, v in d2.items():
                if k == 'info' or k == 'arrays':
                    continue
                if k not in d1:
                    d1[k] = v
                elif v:
                    d1[k] = v

        updated_ids = []
        skipped_ids = []
        upserted_ids = []
        replaced_ids = []
        n_atoms = 0

        for atoms in atoms_list:
            n_atoms += 1

            # Check if it already exists in the database
            if 'uid' in atoms.info and atoms.info['uid'] is not None:
                uid = atoms.info['uid']
                exists = self._uid_exists(uid)
            else:
                uid = None
                exists = False

            # Check if this uid has already been "seen". If yes, skip it.
            if (uid is not None) and uid in (upserted_ids + skipped_ids + updated_ids + replaced_ids):
                continue

            if not exists:
                if upsert:
                    # Insert it
                    ins_uid = self._insert_one_atoms(atoms)
                    upserted_ids.append(ins_uid)
                else:
                    # Skip it
                    skipped_ids.append(uid)
            else:
                query = translate(['uid={}'.format(uid)])
                if not replace:
                    # Get the existing Atoms object from the database
                    atoms_it = self.find(auth_token=auth_token,
                                         filter=query, sort={},
                                         limit=1, keys=None,
                                         omit_keys=False)
                    old_atoms = next(atoms_it)

                     # Convert atoms to dictionaries so it's easier to update them
                    old_atoms_dct = atoms2dict(old_atoms, True)
                    new_atoms_dct = atoms2dict(atoms, True)

                    # Update the atoms
                    update_atoms_dct(old_atoms_dct, new_atoms_dct)

                    # Remove the old atoms and insert their new version
                    self.remove(auth_token, query, True)
                    ins_uid = self._insert_one_atoms(dict2atoms(old_atoms_dct, True))
                    updated_ids.append(ins_uid)
                else:
                    # Replace
                    self.remove(auth_token, query, True)
                    ins_uid = self._insert_one_atoms(atoms)
                    replaced_ids.append(ins_uid)

        msg = 'Updated {}/{} configurations.'.format(len(updated_ids), n_atoms)
        return results.UpdateResult(updated_ids=updated_ids, skipped_ids=skipped_ids,
                                    upserted_ids=upserted_ids, replaced_ids=replaced_ids, msg=msg)

    @require_database
    @read_only
    def remove(self, auth_token, filter, just_one):

        if self.remote:
            cmd = 'remove {} {}'.format(self.database, b64encode(json.dumps(filter)))
            if just_one:
                cmd += ' --just-one'
            return communicate_with_remote(self.remote, cmd)

        if just_one:
            limit = 1
        else:
            limit = 0
        ids = [dct['id'] for dct in self._select(filter, limit=limit)]
        self.connection.delete(ids)
        msg = 'Deleted {}'.format(plural(len(ids), 'row'))
        return results.RemoveResult(removed_count=len(ids), msg=msg)

    @require_database
    def find(self, auth_token, filter, sort, limit, keys, omit_keys):

        if self.remote:
            filter_out = b64encode(json.dumps(filter))
            sort_out = b64encode(json.dumps(sort))
            keys_out = b64encode(json.dumps(keys))
            omit_keys_out = b64encode(json.dumps(omit_keys))

            cmd = 'find {} {}'.format(self.database, filter_out)
            cmd += ' --sort {}'.format(sort_out)
            cmd += ' --limit {}'.format(limit)
            cmd += ' --keys {}'.format(keys_out)
            cmd += ' --omit-keys {}'.format(omit_keys_out)
            atoms_dcts_list = communicate_with_remote(self.remote, cmd)
            return ASEdbSQlite3Backend.Cursor(iter([dict2atoms(dct, True) for dct in atoms_dcts_list]))

        rows_iter = self._select(filter, sort=sort, limit=limit)

        # Convert it to the Atoms iterator.
        return ASEdbSQlite3Backend.Cursor(map(lambda x: row2atoms(x, keys, omit_keys), rows_iter))

    @require_database
    @read_only
    def add_keys(self, auth_token, filter, kvp):

        if self.remote:
            cmd = 'add-keys {} {} {}'.format(self.database, b64encode(json.dumps(filter)),
                    b64encode(json.dumps(kvp)))
            return communicate_with_remote(self.remote, cmd)

        ids = [dct['id'] for dct in self._select(filter)]
        n = self.connection.update(ids, [], **kvp)[0]
        msg = 'Added {} key-value pairs in total to {} configurations'.format(n, len(ids))
        return results.AddKvpResult(modified_ids=[], no_of_kvp_added=n, msg=msg)

    @require_database
    @read_only
    def remove_keys(self, auth_token, filter, keys):

        if self.remote:
            cmd = 'remove-keys {} {} {}'.format(self.database, b64encode(json.dumps(filter)),
                    b64encode(json.dumps(keys)))
            return communicate_with_remote(self.remote, cmd)

        ids = [dct['id'] for dct in self._select(filter)]
        n = self.connection.update(ids, keys)[1]
        msg = 'Removed {} keys in total from {} configurations'.format(n, len(ids))
        return results.RemoveKeysResult(modified_ids=ids, no_of_keys_removed=n, msg=msg)

    def open(self):
        pass

    def close(self):
        pass

    def is_open(self):
        return True
