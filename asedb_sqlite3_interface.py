import glob
import os
import sys
from subprocess import call
from random import randint
from ConfigParser import SafeConfigParser

config_path = os.path.join(os.path.abspath(os.path.dirname(os.path.realpath(__file__))), 'abcd_config.txt')
dbs_path = None
parser = SafeConfigParser()

# Config file doesn't exist. Create it
if not os.path.isfile(config_path):
    ase_path = os.path.expanduser(raw_input('ASE path: '))
    dbs_path = os.path.expanduser(raw_input('Path for the databases folder: '))

    cfg_file = open(config_path,'w')
    parser.add_section('ase-db')
    parser.set('ase-db', 'ase_path', ase_path)
    parser.set('ase-db', 'dbs_path', dbs_path)
    parser.write(cfg_file)
    cfg_file.close()
# Read the config file if it exists
else:
    parser.read(config_path)
    dbs_path = parser.get('ase-db', 'dbs_path')
    sys.path.append(parser.get('ase-db', 'ase_path'))

from ase.db import connect
from ase.db.table import Table, all_columns
from ase.utils import plural
from ase.db.summary import Summary
from ase.io import read as ase_io_read, write as ase_io_write
from ase.db.core import convert_str_to_float_or_str

class ASEdb_SQLite3_interface:
    '''Interface the ase-db SQLite3 backend'''

    def __init__(self, opts, args, verbosity):
        self.user = opts.user
        self.opts = opts
        self.args = args
        self.verbosity = verbosity
        self.dbs_path = dbs_path

        if args:
            # Sanitise it by removing all the slashes and dots
            self.database = os.path.basename(args.pop(0))
        else:
            self.database = None
        self.query = ','.join(args)

        if self.query.isdigit():
            self.query = int(self.query)

        self.add_key_value_pairs = {}
        if self.opts.add_key_value_pairs:
            for pair in self.opts.add_key_value_pairs.split(','):
                key, value = pair.split('=')
                self.add_key_value_pairs[key] = convert_str_to_float_or_str(value)

        if self.opts.delete_keys:
            self.delete_keys = self.opts.delete_keys.split(',')
        else:
            self.delete_keys = []

        if not os.path.isdir(self.dbs_path):
            print self.dbs_path, 'does not exist. Create this directory first.'
            sys.exit()

        if self.user == None:
            home = 'all'
        else:
            home = self.user

        self.root_dir = os.path.join(self.dbs_path, home)
        if not os.path.isdir(self.root_dir):
            print 'You don\'t have access to any databases'
            sys.exit()

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

        con = self.open_connection(file_path)

        columns = list(all_columns)
        c = self.opts.columns
        if c and c.startswith('++'):
            keys = set()
            for row in con.select(self.query,
                                  limit=self.opts.limit, offset=self.opts.offset):
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
        
        table = Table(con, self.verbosity, self.opts.cut)
        table.select(self.query, columns, self.opts.sort, self.opts.limit, self.opts.offset)
        if self.opts.csv:
            table.write_csv()
        else:
            table.write()

    def open_connection(self, db_name, type='extract_from_name', create_indices=True,
            use_lock_file=True, append=True):
        '''Opens a connection to the database with name db_name, which is assumed to be present
            under $dbs_path/$user. Returns the connection (JSONDatabase, SQLite3Database or 
            PostgreSQLDatabase).'''

        file_path = os.path.join(self.root_dir, db_name)
        return connect(file_path, use_lock_file = not self.opts.no_lock_file)

    def out(self, *args):
            if self.verbosity > 0:
                print ' '.join(args)

    def analyse(self):
        '''Analyses the connection'''
        con = self.open_connection(self.database)
        con.analyse()

    def add_from_file(self):
        '''Adds a file to the database. The database is created under $dbs_path/all.'''

        con = self.open_connection(self.database)
        filename = self.opts.add_from_file
        if ':' in filename:
            calculator_name, filename = filename.split(':')
            atoms = get_calculator(calculator_name)(filename).get_atoms()
        else:
            atoms = ase_io_read(filename)
            if isinstance(atoms, list):
                raise RuntimeError('multi-config file formats not yet supported')
        data = {}            
        if self.opts.store_original_file:
            self.add_key_value_pairs['original_file_name'] = filename
            with open(filename) as f:
                original_file_contents = f.read()
            data['original_file_contents'] = original_file_contents
        con.write(atoms, key_value_pairs=self.add_key_value_pairs, data=data,
                  add_from_info_and_arrays=self.opts.all_data)
        self.out('Added {0} from {1}'.format(atoms.get_chemical_formula(),
                                        filename))

    def count(self):
        '''Counts the number of rows present in the database.'''
        con = self.open_connection(self.database)
        n = con.count(self.query)
        print('%s' % plural(n, 'row'))

    def explain(self):
        '''Explain query plan'''
        con = self.open_connection(self.database)
        for dct in con.select(self.query, explain=True,
                              verbosity=self.verbosity,
                              limit=self.opts.limit, offset=self.opts.offset):
            print dct['explain']

    def insert_into(self):
        '''Inserts selected row into another database.'''
        nkvp = 0
        nrows = 0
        con = self.open_connection(self.database)
        with self.open_connection(self.opts.insert_into,
                     use_lock_file=not self.opts.no_lock_file) as con2:
            for dct in con.select(self.query):
                kvp = dct.get('key_value_pairs', {})
                nkvp -= len(kvp)
                kvp.update(self.add_key_value_pairs)
                nkvp += len(kvp)
                if self.opts.unique:
                    dct['unique_id'] = '%x' % randint(16**31, 16**32 - 1)
                con2.write(dct, data=dct.get('data'), **kvp)
                nrows += 1
            
        self.out('Added %s (%s updated)' %
            (plural(nkvp, 'key-value pair'),
             plural(len(self.add_key_value_pairs) * nrows - nkvp, 'pair')))
        self.out('Inserted %s' % plural(nrows, 'row'))

    # TODO: Enable this when remotely querying the database
    def write_to_file(self):
        '''Write the selected atoms to a file'''
        filename = self.opts.write_to_file
        if ':' in filename:
            format, filename = filename.split(':')
        else:
            format = None
        nrows = 0
        list_of_atoms = []
        con = self.open_connection(self.database)
        for row in con.select(self.query):
            atoms = row.toatoms(add_to_info_and_arrays=self.opts.all_data)
            if 'original_file_contents' in atoms.info:
                del atoms.info['original_file_contents']
            list_of_atoms.append(atoms)
            nrows += 1
        if '%' in filename:
            for i, atoms in enumerate(list_of_atoms):
                ase_io_write(filename % i, atoms, format=format)
        else:
            if filename == '-':
                if format is None: format = 'extxyz'
                filename = sys.stdout
            ase_io_write(filename, list_of_atoms, format=format)
        self.out('Wrote %d rows.' % len(list_of_atoms))

    def extract_original_file(self):
        '''Extract an original file stored with -o/--store-original-file'''
        nwrite = 0
        nrow = 0
        con = self.open_connection(self.database)
        for row in con.select(self.query):
            nrow += 1
            if ('original_file_name' not in row.key_value_pairs or
                'original_file_contents' not in row.data):
                self.out('no original file stored for row id=%d' % row.id)
                continue
            original_file_name = row.key_value_pairs['original_file_name']
            # restore to current working directory
            original_file_name = os.path.basename(original_file_name)
            if os.path.exists(original_file_name):
                self.out('original_file_name %s already exists in current ' %
                     original_file_name + 'working directory, skipping write')
                continue
            self.out('Writing %s' % original_file_name)            
            with open(original_file_name, 'w') as original_file:
                original_file.write(row.data['original_file_contents'])
            nwrite += 1            
        self.out('Extracted original output files for %d/%d selected rows' % (nwrite, nrow))

    # TODO: How to get the list of all the keys?
    def modify_keys(self):
        '''Adds and deletes keys'''
        con = self.open_connection(self.database)
        ids = [dct['id'] for dct in con.select(self.query)]
        m, n = con.update(ids, self.delete_keys, **self.add_key_value_pairs)
        self.out('Added %s (%s updated)' %
            (plural(m, 'key-value pair'),
             plural(len(self.add_key_value_pairs) * len(ids) - m, 'pair')))
        self.out('Removed', plural(n, 'key-value pair'))

    def delete(self):
        '''Deletes the selected row'''
        con = self.open_connection(self.database)
        ids = [dct['id'] for dct in con.select(self.query)]
        if ids and not self.opts.yes:
            msg = 'Delete %s? (yes/No): ' % plural(len(ids), 'row')
            if raw_input(msg).lower() != 'yes':
                return
        con.delete(ids)
        self.out('Deleted %s' % plural(len(ids), 'row'))

    '''# UserWarning: No labelled objects found.
    def plot(self):
        if ':' in opts.plot:
            tags, keys = opts.plot.split(':')
            tags = tags.split(',')
        else:
            tags = []
            keys = opts.plot
        keys = keys.split(',')
        plots = collections.defaultdict(list)
        X = {}
        labels = []
        for row in con.select(query, sort=opts.sort):
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
        con = self.open_connection(self.database)
        dct = con.get(self.query)
        summary = Summary(dct)
        summary.write()

    def json(self):
        '''Write json representation of the selected row'''
        con = self.open_connection(self.database)
        dct = con.get(self.query)
        con2 = connect(sys.stdout, 'json', use_lock_file=False)
        kvp = dct.get('key_value_pairs', {})
        con2.write(dct, data=dct.get('data'), **kvp)
    
    # Doesn't work for some reason
    '''def open_web_browser(self):
        import ase.db.app as app
        app.db = con
        app.app.run(host='0.0.0.0', debug=True)'''
