import glob
import os
import sys
from subprocess import call
from random import randint
from ConfigParser import SafeConfigParser

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

from ase.db import connect
from ase.db.table import Table, all_columns
from ase.utils import plural
from ase.db.summary import Summary
from ase.io import read as ase_io_read, write as ase_io_write
from ase.db.core import convert_str_to_float_or_str

class asedb_sqlite3_interface:
    '''Interface the ase-db SQLite3 backend'''

    def __init__(self, args, verbosity, mode):
        if mode not in ('incoming', 'remote', 'local'):
            raise Exception('unrecognised mode: {}'.format(mode))

        self.args = args
        self.user = args.user
        self.verbosity = verbosity
        self.dbs_path = dbs_path
        self.query = args.query
        self.mode = mode
        if args.database:
            self.database = os.path.basename(args.database)
        else:
            self.database = None

        if self.query.isdigit():
            self.query = int(self.query)

        self.add_key_value_pairs = {}
        if self.args.add_key_value_pairs:
            for pair in self.args.add_key_value_pairs.split(','):
                key, value = pair.split('=')
                self.add_key_value_pairs[key] = convert_str_to_float_or_str(value)

        if self.args.delete_keys:
            self.delete_keys = self.args.delete_keys.split(',')
        else:
            self.delete_keys = []

        # Check if the databases directory exists. If not , create it
        if not os.path.isdir(self.dbs_path):
            os.mkdir(dbs_path)
            print self.dbs_path, 'was created'

        # Check if the $databases/all directory exists. If not, create it
        if not os.path.isdir(os.path.join(self.dbs_path, 'all')):
            os.mkdir(os.path.join(dbs_path, 'all'))
            print os.path.join(self.dbs_path,'all'), 'was created'

        # Get the user. If the script is running locally, we have access
        # to all databases.
        if self.user == None:
            home = 'all'
        else:
            home = self.user

        # root_dir is the directory in which user's databases are stored
        self.root_dir = os.path.join(self.dbs_path, home)
        if not os.path.isdir(self.root_dir):
            print 'You don\'t have access to any databases'
            sys.exit()

    def disable_when_incoming(func):
        '''Decorator that disables a function when the remote is being queried.
            It is mainly used to disable write access.'''
        def func_wrapper(self, *args, **kwargs):
            if self.mode == 'incoming':
                raise Exception('Function "{}" is disabled when accessing remote.'.format(func.__name__))
            else:
                func(self, *args, **kwargs)
        return func_wrapper

    def _open_connection(self, db_name, type='extract_from_name', create_indices=True,
            use_lock_file=True, append=True):
        '''Opens a connection to the database with name db_name, which is assumed to be present
            under $dbs_path/$user. Returns the connection (JSONDatabase, SQLite3Database or 
            PostgreSQLDatabase).'''

        file_path = os.path.join(self.root_dir, db_name)
        return connect(file_path, use_lock_file = not self.args.no_lock_file)

    def _out(self, *args):
            if self.verbosity > 0:
                print ' '.join(args)

    def list(self):
        '''Lists all the available databases for the user. Looks under $dbs_path/$user,
        or $dbs_path/all if the program is run locally.'''

        available_dbs = glob.glob(os.path.join(self.root_dir, '*.db'))
        
        if self.user:
            print 'Hello, {}. Databases you have access to:'.format(self.user)
        else:
            print 'Hello Local User. Databases you have access to:'
        for db in available_dbs:
            print '    ', os.path.basename(db)

    def default(self):
        '''Default behaviour when the database name is supplied as an argument'''

        file_path = os.path.join(self.root_dir, self.database)
        if not os.path.isfile(file_path):
            print 'Could not find', self.database
            return

        con = self._open_connection(file_path)

        columns = list(all_columns)
        c = self.args.columns
        if c and c.startswith('++'):
            keys = set()
            for row in con.select(self.query,
                                  limit=self.args.limit, offset=self.args.offset):
                keys.update(row._keys)
            columns.extend(keys)
            if c[2:3] == ',':
                c = c[3:]
            else:
                c = ''
        if c:
            if c[0] == '+':
                c = c[1:]
            elif c[0] != '-':
                columns = []
            for col in c.split(','):
                if col[0] == '-':
                    columns.remove(col[1:])
                else:
                    columns.append(col.lstrip('+'))
        
        table = Table(con, self.verbosity, self.args.cut)
        table.select(self.query, columns, self.args.sort, self.args.limit, self.args.offset)
        if self.args.csv:
            table.write_csv()
        else:
            table.write()

    def analyse(self):
        '''Analyses the connection'''
        con = self._open_connection(self.database)
        con.analyse()

    @disable_when_incoming
    def add_from_file(self):
        '''Adds a file to the database. The database is created under $dbs_path/all.'''

        con = self._open_connection(self.database)
        filename = self.args.add_from_file
        if ':' in filename:
            calculator_name, filename = filename.split(':')
            atoms = get_calculator(calculator_name)(filename).get_atoms()
        else:
            atoms = ase_io_read(filename)
            if isinstance(atoms, list):
                raise RuntimeError('multi-config file formats not yet supported')
        data = {}            
        if self.args.store_original_file:
            self.add_key_value_pairs['original_file_name'] = filename
            with open(filename) as f:
                original_file_contents = f.read()
            data['original_file_contents'] = original_file_contents
        con.write(atoms, key_value_pairs=self.add_key_value_pairs, data=data,
                  add_from_info_and_arrays=self.args.all_data)
        self._out('Added {0} from {1}'.format(atoms.get_chemical_formula(),
                                        filename))

    def count(self):
        '''Counts the number of rows present in the database.'''
        con = self._open_connection(self.database)
        n = con.count(self.query)
        print('%s' % plural(n, 'row'))

    def explain(self):
        '''Explain query plan'''
        con = self._open_connection(self.database)
        for dct in con.select(self.query, explain=True,
                              verbosity=self.verbosity,
                              limit=self.args.limit, offset=self.args.offset):
            print dct['explain']

    @disable_when_incoming
    def insert_into(self):
        '''Inserts selected row into another database.'''
        nkvp = 0
        nrows = 0
        con = self._open_connection(self.database)
        with self._open_connection(self.args.insert_into,
                     use_lock_file=not self.args.no_lock_file) as con2:
            for dct in con.select(self.query):
                kvp = dct.get('key_value_pairs', {})
                nkvp -= len(kvp)
                kvp.update(self.add_key_value_pairs)
                nkvp += len(kvp)
                if self.args.unique:
                    dct['unique_id'] = '%x' % randint(16**31, 16**32 - 1)
                con2.write(dct, data=dct.get('data'), **kvp)
                nrows += 1
            
        self._out('Added %s (%s updated)' %
            (plural(nkvp, 'key-value pair'),
             plural(len(self.add_key_value_pairs) * nrows - nkvp, 'pair')))
        self._out('Inserted %s' % plural(nrows, 'row'))

    def _save_file(self, list_of_atoms, filename, format):
        print format
        if '%' in filename:
            for i, atoms in enumerate(list_of_atoms):
                ase_io_write(filename % i, atoms, format=format)
        else:
            if filename == '-':
                if format is None: format = 'extxyz'
                filename = sys.stdout
            ase_io_write(filename, list_of_atoms, format=format)

    def write_to_file(self, *args, **kwargs):
        '''Write the selected atoms to a file'''

        filename = self.args.write_to_file
        if ':' in filename:
            format, filename = filename.split(':')
        else:
            format = None

        # If the contents are given, save the file locally and return.
        if 'contents' in kwargs:
            with open(filename, 'w') as f:
                f.write(kwargs['contents'])
            return
        
        # Read the configuration from the database
        nrows = 0
        list_of_atoms = []
        con = self._open_connection(self.database)
        for row in con.select(self.query):
            atoms = row.toatoms(add_to_info_and_arrays=self.args.all_data)
            if 'original_file_contents' in atoms.info:
                del atoms.info['original_file_contents']
            list_of_atoms.append(atoms)
            nrows += 1

        # Incoming connection. File will be printed to standard output
        if self.mode == 'incoming':
            filename = '-'

        # Save/print the file
        if '%' in filename:
            for i, atoms in enumerate(list_of_atoms):
                ase_io_write(filename % i, atoms, format=format)
        else:
            if filename == '-':
                if format is None:
                    format = 'extxyz'
                filename = sys.stdout
            ase_io_write(filename, list_of_atoms, format=format)
        
        if self.mode == 'local':
            self._out('Wrote %d rows.' % len(list_of_atoms))

    @disable_when_incoming
    def extract_original_file(self):
        '''Extract an original file stored with -o/--store-original-file'''
        nwrite = 0
        nrow = 0
        con = self._open_connection(self.database)
        for row in con.select(self.query):
            nrow += 1
            if ('original_file_name' not in row.key_value_pairs or
                'original_file_contents' not in row.data):
                self._out('no original file stored for row id=%d' % row.id)
                continue
            original_file_name = row.key_value_pairs['original_file_name']
            # restore to current working directory
            original_file_name = os.path.basename(original_file_name)
            if os.path.exists(original_file_name):
                self._out('original_file_name %s already exists in current ' %
                     original_file_name + 'working directory, skipping write')
                continue
            self._out('Writing %s' % original_file_name)            
            with open(original_file_name, 'w') as original_file:
                original_file.write(row.data['original_file_contents'])
            nwrite += 1            
        self._out('Extracted original output files for %d/%d selected rows' % (nwrite, nrow))

    # TODO: How to get the list of all the keys?
    @disable_when_incoming
    def modify_keys(self):
        '''Adds and deletes keys'''
        con = self._open_connection(self.database)
        ids = [dct['id'] for dct in con.select(self.query)]
        m, n = con.update(ids, self.delete_keys, **self.add_key_value_pairs)
        self._out('Added %s (%s updated)' %
            (plural(m, 'key-value pair'),
             plural(len(self.add_key_value_pairs) * len(ids) - m, 'pair')))
        self._out('Removed', plural(n, 'key-value pair'))

    @disable_when_incoming
    def delete(self):
        '''Deletes the selected row'''
        con = self._open_connection(self.database)
        ids = [dct['id'] for dct in con.select(self.query)]
        if ids and not self.args.yes:
            msg = 'Delete %s? (yes/No): ' % plural(len(ids), 'row')
            if raw_input(msg).lower() != 'yes':
                return
        con.delete(ids)
        self._out('Deleted %s' % plural(len(ids), 'row'))

    '''# UserWarning: No labelled objects found.
    def plot(self):
        if ':' in args.plot:
            tags, keys = args.plot.split(':')
            tags = tags.split(',')
        else:
            tags = []
            keys = args.plot
        keys = keys.split(',')
        plots = collections.defaultdict(list)
        X = {}
        labels = []
        for row in con.select(query, sort=args.sort):
            name = ','.join(row[tag] for tag in tags)
            x = row.get(keys[0])
            if x is not None:
                if isinstance(x, (unicode, str)):
                    if x not in X:
                        X[x] = len(X)
                        labels.append(x)
                    x = X[x]
                plots[name].append([x] + [row.get(key) for key in keys[1:]])
        import matplotlib.pyplot as plt
        for name, plot in plots.items():
            xyy = zip(*plot)
            x = xyy[0]
            for y, key in zip(xyy[1:], keys[1:]):
                plt.plot(x, y, label=name + key)
        if X:
            plt.xticks(range(len(labels)), labels, rotation=90)
        plt.legend()
        plt.show()'''

    def long(self):
        '''Long description of the selected row'''
        con = self._open_connection(self.database)
        dct = con.get(self.query)
        summary = Summary(dct)
        summary.write()

    def json(self):
        '''Write json representation of the selected row'''
        con = self._open_connection(self.database)
        dct = con.get(self.query)
        con2 = connect(sys.stdout, 'json', use_lock_file=False)
        kvp = dct.get('key_value_pairs', {})
        con2.write(dct, data=dct.get('data'), **kvp)
    
    # Doesn't work for some reason
    '''def open_web_browser(self):
        import ase.db.app as app
        app.db = con
        app.app.run(host='0.0.0.0', debug=True)'''
