__author__ = 'Martin Uhrin'

import random
from ase.utils import hill
import time

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

def trim(str, length):
    if len(str) > length:
        return (str[:length] + '..')
    else:
        return str

def atoms_it2table(atoms_it):
    '''Table is a list of dicts'''
    table = []
    for atoms in atoms_it:
        old_dict = atoms2dict(atoms, True)
        
        new_dict = dict(old_dict)
        new_dict.pop('key_value_pairs', None)
        new_dict.pop('data', None)

        if old_dict['key_value_pairs']:
            for key, value in old_dict['key_value_pairs'].iteritems():
                new_dict[key] = old_dict['key_value_pairs'][key]

        new_dict['formula'] = (hill(atoms.numbers))

        table.append(new_dict)
    return table

def keys_union(table):
    keys = set()
    for dct in table:
        for key in dct:
            keys.add(key)
    return list(keys)

def keys_intersection(table):
    if table:
        keys = set(list(table[0].keys()))
    else:
        return set()
    for dct in table[1:]:
        new_keys = set()
        for key in dct:
            new_keys.add(key)
        keys = keys & new_keys
    return list(keys)

def values_range(table, key):
    values = []
    for dct in table:
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
            ret = values[0].__class__
        return ret

def pretty_table(atoms_it):
    table = atoms_it2table(atoms_it)
    keys_list = keys_union(table)

    # Reorder the list
    order = ['id', 'ctime', 'user', 'formula', 'config_type', 'calculator', 
                'calculator_parameters', 'positions', 'energy', 'stress', 
                'forces', 'pbc', 'numbers']
    for key in reversed(order):
        if key in keys_list:
            keys_list.insert(0, keys_list.pop(keys_list.index(key)))

    from prettytable import PrettyTable
    t = PrettyTable([trim(key, 10) for key in keys_list])
    t.padding_width = 0
    for dct in table:
        lst = []
        for key in keys_list:
            if key in dct:
                value = dct[key]
                if key == 'ctime':
                    value = time.strftime('%d/%m/%y %H:%M:%S', time.localtime(value*YEAR+T2000))
                value = trim(str(value), 10)
            else:
                value = '-'
            lst.append(value)
        t.add_row(lst)
    return t.get_string()