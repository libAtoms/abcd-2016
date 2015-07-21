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
    print value_list

    queries = []
    for vals in value_list:
        q = []
        for i, key in enumerate(keys):
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

        # Try to connect to the database if it was supplied as an argument
        if database:
            database = os.path.basename(database)
            if not self.connect_to_database(database):
                raise Exception('{} does not exist'.format(database))

        super(ASEdbSQlite3Backend, self).__init__()

    def _select(self, query, sort=None, limit=0):
        query = translate_query(query)
        rows = []
        ids = []
        for q in query:
            rows_iter = self.connection.select(q, sort=sort, limit=limit)
            print q
            for row in rows_iter:
                if row.unique_id not in ids:
                    rows.append(row)
                    ids.append(row.unique_id)
        if limit != 0 and len(rows) > limit:
            return rows[:limit]
        else:
            return rows

    def list(self, auth_token):
        dbs = glob.glob(os.path.join(self.root_dir, '*.db'))
        return [os.path.basename(db) for db in dbs]

    def authenticate(self, credentials):
        return credentials.username

    def connect_to_database(self, database):
        '''
        Connects to the database if it exists.
        If it doesn't exist, a new database is created.
        '''
        file_path = os.path.join(self.root_dir, database)
        self.connection = connect(file_path)
        return True

    @require_database
    def insert(self, auth_token, atoms, kvp):

        def insert_atoms(atoms):
            atoms.info.pop('id', None)
            if not 'unique_id' in atoms.info:
                atoms.info['unique_id'] = '%x' % randint(16**31, 16**32 - 1)
            return self.connection.write(atoms=atoms, key_value_pairs=kvp, add_from_info_and_arrays=True)

        ids = []
        if isinstance(atoms, Atoms):
            ids.append(insert_atoms(atoms))
        else:
            # Assume it's an iterable
            for ats in atoms:
                ids.append(insert_atoms(ats))
        msg = 'Inserted {} configurations'.format(len(ids))
        return results.InsertResult(inserted_ids=ids, msg=msg)

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
    def find(self, auth_token, filter, sort, limit, keys, omit_keys):
        if not sort:
            sort = 'id'

        rows_iter = self._select(filter, sort=sort, limit=limit)

        def row2atoms(row):
            atoms = row.toatoms(add_to_info_and_arrays=True)
            atoms.info['id'] = row.id
            atoms.info['user'] = row.user
            atoms.info['ctime'] = row.ctime

            keys_to_delete = []
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

    def add_kvp(self, auth_token, filter, kvp):
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
