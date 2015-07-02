from abcd.backend import Backend
import abcd.backend
import abcd.results as results

import os
from ConfigParser import SafeConfigParser
from itertools import imap

from ase.db import connect
from ase.utils import plural
from ase.atoms import Atoms

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

        # Connect to the database if it was supplied as an argument
        if database:
            self.connect_to_database(database)

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

    def authenticate(self, credentials):
        return credentials.username

    def connect_to_database(self, database):
        database = os.path.basename(database)
        file_path = os.path.join(self.root_dir, database)
        self.connection = connect(file_path)

    def insert(self, auth_token, atoms):
        ids = []
        if isinstance(atoms, Atoms):
            ids.append(self.connection.write(atoms=atoms, add_from_info_and_arrays=True))
        else:
            # Assume it's an iterator
            for ats in atoms:
                ids.append(self.connection.write(atoms=ats, add_from_info_and_arrays=True))
        msg = 'Inserted {} configurations'.format(len(ids))
        return results.InsertResult(inserted_ids=ids, msg=msg)

    def remove(self, auth_token, filter, just_one):
        ids = [dct['id'] for dct in self.connection.select(filter)]
        if just_one and ids:
            ids = ids[0:1]
        self.connection.delete(ids)
        msg = 'Deleted {}'.format(plural(len(ids), 'row'))
        return results.RemoveResult(removed_count=len(ids), msg=msg)

    def find(self, auth_token, filter, sort, limit):
        if not sort:
            sort = 'id'
        rows_iter = self.connection.select(filter, sort=sort, limit=limit)

        # Convert it to the Atoms iterator.
        return ASEdbSQlite3Backend.Cursor(
                    imap(lambda x: x.toatoms(add_to_info_and_arrays=True), rows_iter))

    def open(self):
        pass

    def close(self):
        pass

    def is_open(self):
        return True
