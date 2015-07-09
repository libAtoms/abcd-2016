from abcd.backend import Backend
import abcd.backend
import abcd.results as results

import os
from ConfigParser import SafeConfigParser
from itertools import imap

from ase.db import connect
from ase.utils import plural
from ase.atoms import Atoms

from random import randint

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

    def __init__(self, database=None, user=None, password=None):

        self.user = user
        self.dbs_path = self._get_dbs_path()

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

    def _get_dbs_path(self):
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

    def _translate_query(dct_query):
        query = []
        for key, value in dct_query.iteritems():
            query.append('{}={}'.format(key, value))
        return ','.join(query)

    def authenticate(self, credentials):
        return credentials.username

    def connect_to_database(self, database):
        '''
        Connects to the database if it exists.
        If it doesn't exist, a new database is created,
        but this is only possible for the local user.
        '''
        file_path = os.path.join(self.root_dir, database)
        if not os.path.exists(file_path) and self.user:
            return False
        self.connection = connect(file_path)
        return True

    def _insert_atoms(self, atoms):
        atoms.info.pop('id', None)
        if not 'unique_id' in atoms.info:
            atoms.info['unique_id'] = '%x' % randint(16**31, 16**32 - 1)
        return self.connection.write(atoms=atoms, add_from_info_and_arrays=True)

    def insert(self, auth_token, atoms):
        ids = []
        if isinstance(atoms, Atoms):
            ids.append(self._insert_atoms(atoms))
        else:
            # Assume it's an iterator
            for ats in atoms:
                ids.append(self._insert_atoms(atoms))
        msg = 'Inserted {} configurations'.format(len(ids))
        return results.InsertResult(inserted_ids=ids, msg=msg)

    def update(self, auth_token, atoms):
        pass

    def remove(self, auth_token, filter, just_one, confirm):
        if just_one:
            limit = 1
        else:
            limit = 0
        ids = [dct['id'] for dct in self.connection.select(filter, limit=limit)]
        if confirm:
            msg = 'Delete {}? (yes/no): '.format(plural(len(ids), 'row'))
            if raw_input(msg).lower() != 'yes':
                return results.RemoveResult(removed_count=0, 
                                            msg='Operation aborted by the user')
        self.connection.delete(ids)
        msg = 'Deleted {}'.format(plural(len(ids), 'row'))
        return results.RemoveResult(removed_count=len(ids), msg=msg)

    def find(self, auth_token, filter, sort, limit, keys, omit_keys):
        if not sort:
            sort = 'id'
        rows_iter = self.connection.select(filter, sort=sort, limit=limit)

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

    def open(self):
        pass

    def close(self):
        pass

    def is_open(self):
        return True
