__author__ = 'Martin Uhrin'

import random
from ase.utils import hill
import time
from prettytable import PrettyTable

T2000 = 946681200.0  # January 1. 2000
YEAR = 31557600.0  # 365.25 days

def atoms2dict(atoms, include_all_data=False):
    dct = {
        'numbers': atoms.numbers,
        'pbc': atoms.pbc,
        'cell': atoms.cell,
        'positions': atoms.positions,
        'unique_id': '%x' % random.randint(16 ** 31, 16 ** 32 - 1)}
    if atoms.has('magmoms'):
        dct['initial_magmoms'] = atoms.get_initial_magnetic_moments()
    if atoms.has('charges'):
        dct['initial_charges'] = atoms.get_initial_charges()
    if atoms.has('masses'):
        dct['masses'] = atoms.get_masses()
    if atoms.has('tags'):
        dct['tags'] = atoms.get_tags()
    if atoms.has('momenta'):
        dct['momenta'] = atoms.get_momenta()
    if atoms.constraints:
        dct['constraints'] = [c.todict() for c in atoms.constraints]
    if atoms.calc is not None:
        dct['calculator'] = atoms.calc.name.lower()
        dct['calculator_parameters'] = atoms.calc.todict()
        if len(atoms.calc.check_state(atoms)) == 0:
            dct.update(atoms.calc.results)

    if include_all_data:
        # add scalars from Atoms.info to dct['key_value_pairs'] and arrays to dct['data']
        kvp = dct['key_value_pairs'] = {}
        data = dct['data'] = {}
        skip_keys = ['unique_id'] #['calculator', 'id', 'unique_id']
        for (key, value) in atoms.info.items():
            key = key.lower()
            if key in skip_keys:
                continue
            if (isinstance(value, int) or isinstance(value, basestring) or
                    isinstance(value, float) or isinstance(value, bool)):
                # scalar key/value pairs
                kvp[key] = value
            else:
                # more complicated data structures
                data[key] = value

        # add contents of Atoms.arrays to dct['data']
        skip_arrays = ['numbers', 'positions', 'species']
        for (key, value) in atoms.arrays.items():
            if key in skip_arrays:
                continue
            key = key.lower()
            data[key] = value

    return dct

class Table:
    '''
    Class that holds a list of dictionaries (created from the Atoms object).
    '''
    def __init__(self, atoms_it):
        self.dicts = []
        for atoms in atoms_it:
            old_dict = atoms2dict(atoms, True)
            
            new_dict = dict(old_dict)
            new_dict.pop('key_value_pairs', None)
            new_dict.pop('data', None)

            if old_dict['key_value_pairs']:
                for key, value in old_dict['key_value_pairs'].iteritems():
                    new_dict[key] = old_dict['key_value_pairs'][key]

            new_dict['formula'] = (hill(atoms.numbers))
            self.dicts.append(new_dict)

    def _trim(self, str, length):
        if len(str) > length:
            return (str[:length] + '..')
        else:
            return str

    def __str__(self):
        def process_value(key, value):
            if key == 'ctime':
                value = time.strftime('%d/%m/%y %H:%M:%S', 
                        time.localtime(value*YEAR+T2000))
            return self._trim(str(value), 10)

        keys_list = self.keys_union()

        # Reorder the list
        order = ['id', 'ctime', 'user', 'formula', 'config_type', 'calculator', 
                    'calculator_parameters', 'positions', 'energy', 'stress', 
                    'forces', 'pbc', 'numbers']
        for key in reversed(order):
            if key in keys_list:
                keys_list.insert(0, keys_list.pop(keys_list.index(key)))

        t = PrettyTable([self._trim(key, 10) for key in keys_list])
        t.padding_width = 0
        for dct in self.dicts:
            lst = []
            for key in keys_list:
                if key in dct:
                    value = process_value(key, dct[key])       
                else:
                    value = '-'
                lst.append(value)
            t.add_row(lst)
        return t.get_string()

    def values_range(self, key):
        values = []
        for dct in self.dicts:
            if key in dct:
                values.append(dct[key])
        if not values:
            return None
        elif len(values) == 1:
            return (values[0])
        else:
            try:
                ret = (min(values), max(values))
            except:
                ret = ('?', '?')
            return ret

    def keys_union(self):
        keys = set()
        for dct in self.dicts:
            for key in dct:
                keys.add(key)
        return list(keys)

    def keys_intersection(self):
        if self.dicts:
            keys = set(list(self.dicts[0].keys()))
        else:
            return set()
        for dct in self.dicts[1:]:
            new_keys = set()
            for key in dct:
                new_keys.add(key)
            keys = keys & new_keys
        return list(keys)

    def print_keys_table(self):
        union = self.keys_union()
        intersection = self.keys_intersection()
        ranges = {key: self.values_range(key) for key in union}

        t = PrettyTable(['Key', 'Min', 'Max'])
        t.padding_width = 0
        t.align["Key"] = "l"

        print '\nUNION:'
        for key in union:
            row = [key, ranges[key][0], ranges[key][1]]
            t.add_row([self._trim(str(el), 15) for el in row])
        print t

        print '\nINTERSECTION:'
        for key in intersection:
            row = [key, ranges[key][0], ranges[key][1]]
            t.add_row([self._trim(str(el), 15) for el in row])
        print t
