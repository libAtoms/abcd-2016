__author__ = 'Martin Uhrin'

import random


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
        skip_keys = ['calculator', 'id', 'unique_id']
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
