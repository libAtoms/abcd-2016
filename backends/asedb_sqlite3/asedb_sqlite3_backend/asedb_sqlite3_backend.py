from abcd.backend import Backend
import abcd.backend
import abcd.results as results
from abcd.query import Condition, And

from ase.db import connect
from ase.utils import plural
from ase.atoms import Atoms

import os
from ConfigParser import SafeConfigParser
from itertools import imap, product
from random import randint
import glob
import time

def translate_query(conditions):

    # Split conditions with ANDed operands into
    # multiple conditions
    new_conditions = []
    for i, cond in enumerate(conditions):
        if cond.operand.linking_operator == 'and':
            for val in cond.operand.list:
                new_c = Condition(cond.key, cond.operator, And(val))
                new_conditions.append(new_c)
        else:
            new_conditions.append(cond)
    conditions = new_conditions

    keys = [cond.key for cond in conditions]
    operators = [cond.operator for cond in conditions]
    link_operators = [cond.operand.linking_operator for cond in conditions]
    value_list = list(product(*[cond.operand.list for cond in conditions]))

    queries = []
    for vals in value_list:
        q = []
        for i, key in enumerate(keys):
            if key == 'elements' and operators[i] == '~':
                q.append(vals[i])
            elif key == 'elements' and operators[i] != '~':
                raise RuntimeError('"elements" key can only be used with "~"')
            elif operators[i] == '~' and key != 'elements':
                raise RuntimeError('"~" can only be used with the "elements" key')
            else:
                q.append('{}{}{}'.format(key, operators[i], vals[i]))
        queries.append(','.join(q))

    return queries

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
            if not args[0].connection:
                raise Exception("No database is specified")
            else:
                return func(*args, **kwargs)
        return func_wrapper

    def __init__(self, database=None, user=None, password=None):

        def get_dbs_path():
            config_path = os.path.join(os.environ['HOME'], '.abcd_config')
            dbs_path = None
            parser = SafeConfigParser()

            # Config file doesn't exist. Create it
            if not os.path.isfile(config_path):
                dbs_path = os.path.expanduser(raw_input('Path for the databases folder: '))
                cfg_file = open(config_path,'w')
                parser.add_section('ase-db')
                parser.set('ase-db', 'dbs_path', dbs_path)
                parser.write(cfg_file)
                cfg_file.close()
            # Read the config file if it exists
            else:
                parser.read(config_path)
                dbs_path = parser.get('ase-db', 'dbs_path')
            return dbs_path

        self.user = user
        self.dbs_path = get_dbs_path()
        self.connection = None
        self.root_dir = None

        # Check if the databases directory exists. If not , create it
        if not os.path.isdir(self.dbs_path):
            os.mkdir(self.dbs_path)
            print self.dbs_path, 'was created'

        # Check if the $databases/all directory exists. If not, create it
        if not os.path.isdir(os.path.join(self.dbs_path, 'all')):
            os.mkdir(os.path.join(self.dbs_path, 'all'))
            print os.path.join(self.dbs_path,'all'), 'was created'

        # Get the user. If the script is running locally, we have access
        # to all databases.
        if self.user:
            home = self.user
        else:
            home = 'all'

        # root_dir is the directory in which user's databases are stored
        self.root_dir = os.path.join(self.dbs_path, home)

        if database:
            self.connect_to_database(database)

        super(ASEdbSQlite3Backend, self).__init__()

    def _select(self, query, sort=None, reverse=False, limit=0):
        query = translate_query(query)
        rows = []
        ids = []
        for q in query:
            rows_iter = self.connection.select(q, sort=sort, limit=limit)
            for row in rows_iter:
                if row.key_value_pairs['uid'] not in ids:
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
        return credentials.username

    def connect_to_database(self, database, create_new=True):
        '''
        Connnects to a database with given name. If it doesn't
        exist, a new one is created.
        '''
        if '.db' not in database:
            database += '.db'

        # Look inside the root_dir to see if the datbase exists
        if not os.path.isfile(os.path.join(self.root_dir, database)):
            if not create_new:
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

    @require_database
    def insert(self, auth_token, atoms, kvp):

        def insert_atoms(atoms, inserted_ids, skipped_ids):
            atoms.info.pop('id', None)

            # Check if it already exists in the database
            exists = False
            if 'uid' in atoms.info:
                uid = atoms.info['uid']
                query = 'uid={}'.format(uid)
                rows_it = self.connection.select(query, limit=0)
                if sum(1 for _ in rows_it) != 0:
                    exists = True

            if not exists:
                # Add a unique id if it's not present
                if not 'uid' in atoms.info:
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

                self.connection.write(atoms=atoms, key_value_pairs=kvp, add_from_info_and_arrays=True)
                inserted_ids.append(uid)
            else:
                skipped_ids.append(uid)

        inserted_ids = []
        skipped_ids = []
        n_atoms = 0
        if isinstance(atoms, Atoms):
            insert_atoms(atoms, inserted_ids, skipped_ids)
            n_atoms += 1
        else:
            # Assume it's an iterable
            for ats in atoms:
                insert_atoms(ats, inserted_ids, skipped_ids)
                n_atoms += 1
        msg = 'Inserted {}/{} configurations.'.format(len(inserted_ids), n_atoms)
        return results.InsertResult(inserted_ids=inserted_ids, skipped_ids=skipped_ids, msg=msg)

    @require_database
    def update(self, auth_token, atoms):
        return results.UpdateResult(updated_ids=[], msg='')

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

        def row2atoms(row):
            atoms = row.toatoms(add_to_info_and_arrays=True)

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

        # Convert it to the Atoms iterator.
        return ASEdbSQlite3Backend.Cursor(imap(row2atoms, rows_iter))

    def add_keys(self, auth_token, filter, kvp):
        ids = [dct['id'] for dct in self._select(filter)]
        n = self.connection.update(ids, [], **kvp)[0]
        msg = 'Added {} key-value pairs in total to {} configurations'.format(n, len(ids))
        return results.AddKvpResult(modified_ids=[], no_of_kvp_added=n, msg=msg)

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
