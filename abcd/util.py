__author__ = 'Martin Uhrin'

import random
from ase.utils import hill
import time
from prettytable import PrettyTable
import numpy as np
from ase.atoms import Atoms
from ase.calculators.calculator import get_calculator, all_properties
from ase.calculators.singlepoint import SinglePointCalculator

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

def atoms2plaindict(atoms):
    dct = {
        'numbers': atoms.numbers,
        'pbc': atoms.pbc,
        'cell': atoms.cell,
        'positions': atoms.positions}
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

    for key, value in dct.iteritems():
        if value.__class__ == np.ndarray:
            dct[key] = value.tolist()

    info = dct['info'] = {}
    arrays = dct['arrays'] = {}
    for (key, value) in atoms.info.items():
        key = key.lower()
        if (isinstance(value, int) or isinstance(value, basestring) or
                isinstance(value, float) or isinstance(value, bool)):
            # Scalars
            info[key] = value
        else:
            # More complicated data structures
            arrays[key] = value

    skip_arrays = ['numbers', 'positions', 'species']
    for (key, value) in atoms.arrays.iteritems():
        if key in skip_arrays:
            continue
        key = key.lower()
        arrays[key] = value

    for key, value in dct['arrays'].iteritems():
        if value.__class__ == np.ndarray:
            dct['arrays'][key] = value.tolist() 
    return dct

def plaindict2atoms(dct):

    def get_val(dct, key, default=None):
        if key in dct:
            return dct[key]
        return default

    atoms = Atoms(dct['numbers'],
                      dct['positions'],
                      cell=dct['cell'],
                      pbc=dct['pbc'],
                      magmoms=get_val(dct, 'initial_magmoms'),
                      charges=get_val(dct, 'initial_charges'),
                      tags=get_val(dct, 'tags'),
                      masses=get_val(dct, 'masses'),
                      momenta=get_val(dct, 'momenta'),
                      constraint=get_val(dct, 'constraints'))

    results = {}
    for prop in all_properties:
        if prop in dct:
            results[prop] = dct[prop]
    if results:
        atoms.calc = SinglePointCalculator(atoms, **results)
        atoms.calc.name = dct['calculator']

    atoms.info['unique_id'] = get_val(dct, 'unique_id')
    
    if 'arrays' in dct:
        for key, value in dct['arrays'].iteritems():
            key = str(key) # avoid unicode strings
            value = np.array(value)
            if value.dtype.kind == 'U':
                value = value.astype(str)
            try:
                atoms.new_array(key, value)
            except (TypeError, ValueError):
                atoms.info[key] = value
    if 'info' in dct:
        for key, value in dct['info'].iteritems():
            key = str(key)
            atoms.info[key] = value
    return atoms

class Table(object):
    '''
    Class that holds a list of dictionaries (created from the Atoms object).
    '''
    def __init__(self, atoms_it):
        self.dicts = []
        for atoms in atoms_it:
            old_dict = atoms2plaindict(atoms)
            
            new_dict = dict(old_dict)
            new_dict.pop('info', None)
            new_dict.pop('arrays', None)

            if old_dict['info']:
                for key, value in old_dict['info'].iteritems():
                    new_dict[key] = old_dict['info'][key]

            new_dict['formula'] = (hill(atoms.numbers))
            self.dicts.append(new_dict)

    def _trim(self, str, length):
        if len(str) > length:
            return (str[:length] + '..')
        else:
            return str

    def _format_value(self, key, value, max_len):
        if key == 'ctime':
            value = time.strftime('%d/%m/%y %H:%M:%S', 
                    time.localtime(value*YEAR+T2000))
        return self._trim(str(value), max_len)

    def __str__(self):
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
                    value = self._format_value(key, dct[key], 10)
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
        return sorted(list(keys))

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
        return sorted(list(keys))

    def print_keys_table(self):
        union = self.keys_union()
        intersection = self.keys_intersection()
        ranges = {key: self.values_range(key) for key in union}

        t_intersection = PrettyTable(['Key', 'Min', 'Max'])
        t_intersection.padding_width = 0
        t_intersection.align["Key"] = "l"

        print '\nINTERSECTION:'
        for key in intersection:
            row = [key, self._format_value(key, ranges[key][0], 18), 
                        self._format_value(key, ranges[key][1], 18)]
            t_intersection.add_row(row)
        print t_intersection

        t_union = PrettyTable(['Key', 'Min', 'Max'])
        t_union.padding_width = 0
        t_union.align["Key"] = "l"

        print '\nUNION:'
        for key in union:
            row = [key, self._format_value(key, ranges[key][0], 18), 
                        self._format_value(key, ranges[key][1], 18)]
            t_union.add_row(row)
        print t_union
