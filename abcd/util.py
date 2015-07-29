__author__ = 'Martin Uhrin'

import numpy as np
from ase.atoms import Atoms
from ase.calculators.calculator import get_calculator, all_properties
from ase.calculators.singlepoint import SinglePointCalculator

def get_info_and_arrays(atoms, plain_arrays):
    info = {}
    arrays = {}
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

    if plain_arrays:
        for key, value in arrays.iteritems():
            if value.__class__ == np.ndarray:
                arrays[key] = value.tolist()

    return info, arrays

def atoms2dict(atoms, plain_arrays):
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

    if plain_arrays:
        for key, value in dct.iteritems():
            if value.__class__ == np.ndarray:
                dct[key] = value.tolist()

    info, arrays = get_info_and_arrays(atoms, plain_arrays)
    dct['info'] = info
    dct['arrays'] = arrays
    return dct

def dict2atoms(dct, plain_arrays):

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

    atoms.info['uid'] = get_val(dct, 'uid')
    
    if 'arrays' in dct:
        for key, value in dct['arrays'].iteritems():
            key = str(key) # avoid unicode strings
            if plain_arrays:
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