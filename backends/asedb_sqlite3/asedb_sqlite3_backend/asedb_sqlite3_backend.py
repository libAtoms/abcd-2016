from abcd.backend import Backend, ReadError, WriteError
import abcd.backend
import abcd.results as results
from abcd.util import get_info_and_arrays, atoms2dict, dict2atoms
from abcd.authentication import AuthenticationError
from abcd.query import QueryError, translate

from ase.db import connect
from ase.utils import plural
from ase.atoms import Atoms
from ase.calculators.calculator import all_properties
from ase.calculators.singlepoint import SinglePointCalculator

from mongodb2asedb import translate_query
from util import setup, add_user, get_dbs_path, reserved_usernames

import os
import re
from itertools import imap
from random import randint
import glob
import time
import numpy as np

def row2atoms(row, keys, omit_keys):
    atoms = row.toatoms()

    # Add additional info
    atoms.info['unique_id'] = row.unique_id
    if row._keys:
        atoms.info.update(row.key_value_pairs)

    data = row.get('data')
    if data:
        for (key, value) in data.items():
            key = str(key) # avoid unicode strings
            value = np.array(value)
            if value.dtype.kind == 'U':
                value = value.astype(str)
            try:
                atoms.new_array(key, value)
            except (TypeError, ValueError):
                atoms.info[key] = value

    keys_to_delete = ['unique_id']
    if keys != '++':
        for key in atoms.info:
            if key not in keys:
                keys_to_delete.append(key)

    for key in omit_keys:
        keys_to_delete.append(key)

    for key in keys_to_delete:
        atoms.info.pop(key, None)

    return atoms

class ASEdbSQlite3Backend(Backend):

    class Cursor(abcd.backend.Cursor):
        def __init__(self, iterator):
            self.iterator = iterator

        def next(self):
            return self.iterator.next()

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

    def __init__(self, database=None, user=None, password=None, readonly=True):
        if user == 'all':
            raise RuntimeError('Invalid username: '.format('all'))
        self.user = user
        self.readonly = readonly
        self.dbs_path = get_dbs_path()
        self.connection = None
        self.root_dir = None

        # Check if the $databases/all directory exists.
        all_path = os.path.join(self.dbs_path, 'all')
        if not os.path.isdir(all_path):
            cmd = 'python asedb_sqlite3_backend.py --setup'
            raise RuntimeError('{} does not exist. Run "{}" first'.format(all_path, cmd))

        # Get the user. If the script is running locally, we have access
        # to all databases.
        if self.user:
            home = self.user
        else:
            home = 'all'

        # root_dir is the directory in which user's databases are stored
        self.root_dir = os.path.join(self.dbs_path, home)

        # Make sure the database name is safe
        if database is not None and database != '':
            if not re.match(r'^[A-Za-z0-9_]+$', database):
                raise RuntimeError('The database name can only contain alphanumeric characters and underscores.')
            self.connect_to_database(database)

        super(ASEdbSQlite3Backend, self).__init__()

    def _select(self, query, sort=None, reverse=False, limit=0):
        query = translate_query(query)
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
        dbs = glob.glob(os.path.join(self.root_dir, '*.db'))
        return [os.path.basename(db) for db in dbs]

    def authenticate(self, credentials):
        if credentials.username in reserved_usernames:
            raise AuthenticationError('Username "{}" is reserved'.format(credentials.username))
        return credentials.username

    def connect_to_database(self, database):
        '''
        Connnects to a database with given name. If it doesn't
        exist, a new one is created.
        '''
        if '.db' not in database:
            database += '.db'

        # For security reasons
        database = os.path.basename(database)

        # Look inside the root_dir to see if the datbase exists
        if not os.path.isfile(os.path.join(self.root_dir, database)):
            if self.readonly:
                raise RuntimeError('Database {} does not exist'.format(database))
            else:
                # Database does not exist. Create a new one.
                if self.user:
                    new_db_name = '_' + self.user + '_' + database
                else:
                    new_db_name = database
                new_db_path = os.path.join(self.dbs_path, 'all', new_db_name)
                self.connection = connect(new_db_path)

                # Create a symlink
                if self.user:
                    user_db_path = os.path.join(self.root_dir, database)
                    os.symlink(new_db_path, user_db_path)
        else:
            # Database exists. Connect to it.
            db_path = os.path.join(self.root_dir, database)
            self.connection = connect(db_path)

    @read_only
    @require_database
    def insert(self, auth_token, atoms, kvp, overwrite):

        def preprocess(atoms):
            '''
            Load capitalised special key-value pairs into
            a calcuator.
            '''
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

        def insert_atoms(atoms, inserted_ids, skipped_ids, replaced_ids):
            atoms.info.pop('id', None)

            # Check if it already exists in the database
            exists = False
            if 'uid' in atoms.info and atoms.info['uid'] is not None:
                uid = atoms.info['uid']

                # Check if this uid has already been "seen". If yes, skip it.
                if (uid in inserted_ids) or (uid in skipped_ids) or (uid in replaced_ids):
                    return

                query = 'uid={}'.format(uid)
                rows_it = self.connection.select(query, limit=0)
                if sum(1 for _ in rows_it) != 0:
                    exists = True

            if not exists or overwrite:
                # Add a unique id if it's not present
                if not 'uid' in atoms.info or atoms.info['uid'] is None:
                    atoms.info['uid'] = '%x' % randint(16**14, 16**15 - 1)
                uid = atoms.info['uid']

                # Add a creation time if it's not present
                if not 'c_time' in atoms.info:
                    atoms.info['c_time'] = int(time.time())

                # Change the modification time
                atoms.info['m_time'] = int(time.time())

                # Update the formula and n_atoms
                atoms.info['formula'] = atoms.get_chemical_formula()
                atoms.info['n_atoms'] = len(atoms.numbers)

                preprocess(atoms)
                info, arrays = get_info_and_arrays(atoms, plain_arrays=False)

                if exists:
                    # Remove the original configuration (it will be replaced)
                    query = translate(['uid={}'.format(atoms.info['uid'])])
                    self.remove(auth_token, query, True, False)

                self.connection.write(atoms=atoms, key_value_pairs=info, data=arrays)

                if exists:
                    replaced_ids.append(uid)
                else:
                    inserted_ids.append(uid)
            else:
                skipped_ids.append(uid)

        inserted_ids = []
        skipped_ids = []
        replaced_ids = []
        n_atoms = 0
        if isinstance(atoms, Atoms):
            insert_atoms(atoms, inserted_ids, skipped_ids, replaced_ids)
            n_atoms += 1
        else:
            # Assume it's an iterable
            for ats in atoms:
                insert_atoms(ats, inserted_ids, skipped_ids, replaced_ids)
                n_atoms += 1
        msg = 'Inserted {}/{} configurations.'.format(len(inserted_ids), n_atoms)
        return results.InsertResult(inserted_ids=inserted_ids, skipped_ids=skipped_ids, replaced_ids=replaced_ids, msg=msg)

    @read_only
    @require_database
    def update(self, auth_token, atoms, upsert):
        '''Takes the Atoms object or a list of Atoms objects'''

        def update_atoms_dct(d1, d2):
            # Update info and arrays
            if 'info' in d1 and 'info' in d2:
                d1['info'].update(d2['info'])
            if 'arrays' in d1 and 'arrays' in d2:
                d1['arrays'].update(d2['arrays'])
            # Update the rest
            for k, v in d2.iteritems():
                if k == 'info' or k == 'arrays':
                    continue
                if k not in d1:
                    d1[k] = v
                elif v:
                    d1[k] = v

        def update_atoms(atoms, updated_ids, skipped_ids, inserted_ids):
            '''Takes the Atoms object (not a list)'''

            if 'uid' in atoms.info and atoms.info['uid'] is not None:
                uid = atoms.info['uid']

                # Check if this uid has already been "seen". If yes, skip it.
                if (uid in inserted_ids) or (uid in updated_ids) or (uid in skipped_ids):
                    return

                query = translate(['uid={}'.format(uid)])
                atoms_it = self.find(auth_token, query, None, False, 1, '++', [])

                old_atoms = None
                try:
                    old_atoms = next(atoms_it)
                except StopIteration:
                    # Iterator is empty, this uid does not exist yet
                    if upsert:
                        self.insert(auth_token, atoms, {}, False)
                        inserted_ids.append(uid)
                    else:
                        skipped_ids.append(uid)
                    return

                def print_dct(dct):
                    for k, v in dct.iteritems():
                        if k != 'original_file_contents':
                            print k, v
                    print ''

                # Convert atoms to dictionaries so it's easier to update them
                old_atoms_dct = atoms2dict(old_atoms, True)
                new_atoms_dct = atoms2dict(atoms, True)

                # Update the atoms
                update_atoms_dct(old_atoms_dct, new_atoms_dct)

                # Remove the old atoms and insert their new version
                self.remove(auth_token, query, True, False)
                self.insert(auth_token, dict2atoms(old_atoms_dct, True), {}, False)
                updated_ids.append(uid)
            elif upsert:
                res = self.insert(auth_token, atoms, {}, False)
                inserted_ids.append(res.inserted_ids[0])
            else:
                # Configuration doesn't have uid
                skipped_ids.append('(no id)')

        updated_ids = []
        skipped_ids = []
        inserted_ids = []
        n_atoms = 0
        if isinstance(atoms, Atoms):
            update_atoms(atoms, updated_ids, skipped_ids, inserted_ids)
            n_atoms += 1
        else:
            # Assume it's an iterable
            for ats in atoms:
                update_atoms(ats, updated_ids, skipped_ids, inserted_ids)
                n_atoms += 1

        msg = 'Updated {}/{} configurations.'.format(len(updated_ids), n_atoms)
        return results.UpdateResult(updated_ids=updated_ids, skipped_ids=skipped_ids, inserted_ids=inserted_ids, msg=msg)

    @read_only
    @require_database
    def remove(self, auth_token, filter, just_one, confirm):
        if just_one:
            limit = 1
        else:
            limit = 0
        ids = [dct['id'] for dct in self._select(filter, limit=limit)]
        if confirm:
            msg = 'Delete {}? (yes/no): '.format(plural(len(ids), 'row'))
            if raw_input(msg).lower() != 'yes':
                return results.RemoveResult(removed_count=0, 
                                            msg='Operation aborted by the user')
        self.connection.delete(ids)
        msg = 'Deleted {}'.format(plural(len(ids), 'row'))
        return results.RemoveResult(removed_count=len(ids), msg=msg)

    @require_database
    def find(self, auth_token, filter, sort, reverse, limit, keys, omit_keys):
        if not sort:
            sort = 'id'
        rows_iter = self._select(filter, sort=sort, reverse=reverse, limit=limit)

        # Convert it to the Atoms iterator.
        return ASEdbSQlite3Backend.Cursor(imap(lambda x: row2atoms(x, keys, omit_keys), rows_iter))

    @read_only
    def add_keys(self, auth_token, filter, kvp):
        ids = [dct['id'] for dct in self._select(filter)]
        n = self.connection.update(ids, [], **kvp)[0]
        msg = 'Added {} key-value pairs in total to {} configurations'.format(n, len(ids))
        return results.AddKvpResult(modified_ids=[], no_of_kvp_added=n, msg=msg)

    @read_only
    def remove_keys(self, auth_token, filter, keys):
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

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]

    if args[0] == '--setup' and len(args) == 1:
        setup()
    elif args[0] == '--add-user' and len(args) == 2:
        add_user(args[1])
    else:
        print 'Usage: python asedb_sqlite3_backend.py --setup / --add-user USER'
