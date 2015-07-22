__author__ = 'Martin Uhrin'

import random
import numpy as np
from ase.atoms import Atoms
from ase.calculators.calculator import get_calculator, all_properties
from ase.calculators.singlepoint import SinglePointCalculator

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