__author__ = 'Martin Uhrin'

import random
from ase.utils import hill

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

def atoms_it2table(atoms_it):
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

    keys = set()
    for dct in table:
        for key in dct:
            keys.add(key)
    keys_list = list(keys)

    # Reorder the list
    order = ['id', 'user', 'ctime', 'formula']
    for key in reversed(order):
        if key in keys_list:
            keys_list.insert(0, keys_list.pop(keys_list.index(key)))

    from prettytable import PrettyTable
    t = PrettyTable(keys_list)
    t.padding_width = 0
    for dct in table:
        lst = []
        for key in keys_list:
            if key in dct:
                value = dct[key]
                value = str(value)
                value = (value[:10] + '..') if len(value) > 10 else value
            else:
                value = '-'
            lst.append(value)
        t.add_row(lst)
    return t.get_string()