__author__ = 'Martin Uhrin, Patrick Szmucer'

import numpy as np
from ase.atoms import Atoms
from ase.calculators.calculator import get_calculator, all_properties
from ase.calculators.singlepoint import SinglePointCalculator
from six import string_types


def filter_keys(keys_list, keys, omit_keys):
    '''Decides which keys to show given keys and omit_keys'''

    new_keys_list = list(keys_list)
    if omit_keys:
        if keys is not None:
            for key in keys_list:
                if key in keys:
                    new_keys_list.remove(key)
        else:
            # Omit all keys
            new_keys_list = []
    else:
        if keys is not None:
            for key in keys_list:
                if key not in keys:
                    new_keys_list.remove(key)
    return new_keys_list


def get_info_and_arrays(atoms, plain_arrays):
    """
    Extracts the info and arrays dictionaries from the Atoms object.
    If plain_arrays is True, numpy arrays are converted to lists.
    """
    info = {}
    arrays = {}
    for (key, value) in list(atoms.info.items()):
        key = key.lower()
        # TODO: all scalar values? test...
        if (isinstance(value, int) or isinstance(value, string_types) or
            isinstance(value, float) or isinstance(value, bool)):
            # Scalars
            info[key] = value
        else:
            # More complicated data structures
            arrays[key] = value

    skip_arrays = ['numbers', 'positions', 'species']
    for (key, value) in atoms.arrays.items():
        if key in skip_arrays:
            continue
        key = key.lower()
        arrays[key] = value

    if plain_arrays:
        for key, value in arrays.items():
            if value.__class__ == np.ndarray:
                arrays[key] = value.tolist()

    return info, arrays


def atoms2dict(atoms, plain_arrays=False):
    """
    Converts the Atoms object to a dictionary. If plain_arrays is True,
    numpy arrays are converted to lists.
    """
    d = {
        'numbers': atoms.numbers,
        'pbc': atoms.pbc,
        'cell': atoms.cell,
        'positions': atoms.positions}
    if atoms.has('magmoms'):
        d['initial_magmoms'] = atoms.get_initial_magnetic_moments()
    if atoms.has('charges'):
        d['initial_charges'] = atoms.get_initial_charges()
    if atoms.has('masses'):
        d['masses'] = atoms.get_masses()
    if atoms.has('tags'):
        d['tags'] = atoms.get_tags()
    if atoms.has('momenta'):
        d['momenta'] = atoms.get_momenta()
    if atoms.constraints:
        d['constraints'] = [c.todict() for c in atoms.constraints]
    if atoms.calc is not None:
        d['calculator'] = atoms.calc.name.lower()
        d['calculator_parameters'] = atoms.calc.todict()
        if len(atoms.calc.check_state(atoms)) == 0:
            d.update(atoms.calc.results)

    if plain_arrays:
        for key, value in d.items():
            if value.__class__ == np.ndarray:
                d[key] = value.tolist()

    info, arrays = get_info_and_arrays(atoms, plain_arrays)
    d['info'] = info
    d['arrays'] = arrays
    return d


def dict2atoms(d, plain_arrays=False):
    """
    Converts a dictionary created with atoms2dict back to atoms.
    """
    atoms = Atoms(d['numbers'],
                  d['positions'],
                  cell=d['cell'],
                  pbc=d['pbc'],
                  magmoms=d.get('initial_magmoms'),
                  charges=d.get('initial_charges'),
                  tags=d.get('tags'),
                  masses=d.get('masses'),
                  momenta=d.get('momenta'),
                  constraint=d.get('constraints'))

    results = {}
    for prop in all_properties:
        if prop in d:
            results[prop] = d[prop]
    if results:
        atoms.calc = SinglePointCalculator(atoms, **results)
        atoms.calc.name = d['calculator']

    atoms.info['uid'] = d.get('uid')

    if 'arrays' in d:
        for key, value in d['arrays'].items():
            key = str(key)  # avoid unicode strings
            if plain_arrays:
                value = np.array(value)
            if value.dtype.kind == 'U':
                value = value.astype(str)
            try:
                atoms.new_array(key, value)
            except (TypeError, ValueError):
                atoms.info[key] = value
    if 'info' in d:
        for key, value in d['info'].items():
            atoms.info[str(key)] = value
    return atoms
