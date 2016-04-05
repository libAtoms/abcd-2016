"""
abcd.util.atoms

Functions to process atoms objects between formats or extract information
from them.

"""

import io
import os
import tarfile
from base64 import b64decode
from os import path

import numpy as np
import ase.io
from ase.atoms import Atoms
from ase.calculators.calculator import get_calculator, all_properties
from ase.calculators.singlepoint import SinglePointCalculator
from six import string_types

from abcd.util.text import filename_enumerator

__author__ = 'Martin Uhrin, Patrick Szmucer'


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


def atoms_to_files(atoms, filename, format=None):
    """
    Write the atoms to a file or files.

    Parameters
    ----------
    atoms : ase.Atoms or list of ase.Atoms
        Configurations to write to files.
    filename : str
        A single file name, or a string that can be formatted using {}
        formats or % interpolation.
    format : str, optional
        Output format to pass to ase, if not given, ase will try to guess
        from the filename.

    Returns
    -------
    num_configs, num_files : int, int
        The number of configurations, and the number of files written

    """

    # Always work with multiconfigurations, even for single configurations
    if isinstance(atoms, Atoms):
        atoms = [atoms]

    # ensure extxyz for xyz files, but let
    # ase write take care of other formats itself.
    if filename.endswith('.xyz') and not format:
        format = 'extxyz'

    # TODO: iterator for large numbers of configurations?
    # TODO: format strings with atoms properties?
    # TODO: output to specific path

    # incorporate index in filename
    enumerator = filename_enumerator(filename)
    if enumerator is None:
        # Dump all as a single file, one filename.
        config_path = path.dirname(filename)
        if config_path and not path.isdir(config_path):
            os.makedirs(config_path)
        ase.io.write(filename, atoms, format=format)
        return 1, len(atoms)
    else:
        # We can have multiple files! In multiple directories
        # count files rather than use idx so that we correctly get the 0 case
        file_count = 0
        for idx, config in enumerate(atoms):
            config_filename = enumerator(idx)
            config_path = path.dirname(config_filename)
            if config_path and not path.isdir(config_path):
                os.makedirs(config_path)
            ase.io.write(config_filename, config, format=format)
            file_count += 1
        return file_count, file_count


def extract_original_file(atoms, workdir='.', untar=False):
    """
    Given a single Atoms object, retrieve the original files that were
    used to create it (stored in 'original_files').

    Parameters
    ----------
    atoms : ase.Atoms
        Configuration from which to extract the original files.

    Returns
    -------
    number_of_files : int
        The number of files created, either a tar file or the number of
        extracted files.

    """

    if 'original_files' in atoms.info:
        contents = atoms.info['original_files']
    elif 'original_files' in atoms.arrays:
        contents = atoms.arrays['original_files']
    elif 'original_file_contents' in atoms.info:
        contents = atoms.info['original_file_contents']
    elif 'original_file_contents' in atoms.arrays:
        contents = atoms.arrays['original_file_contents']
    else:
        # Nothing to extract
        return False

    if untar:
        # Don't create a temporary file just extract in memory
        contents_bytes = io.BytesIO(b64decode(contents))
        tar = tarfile.open(fileobj=contents_bytes, mode='r')
        file_count = len(tar.getmembers())
        tar.extractall(path=workdir)
        tar.close()
        contents_bytes.close()
        return file_count
    else:
        # TODO: atoms with no uid should not clobber each other
        # use 0 when no uid is present
        tar_name = "{0}-{1}.tar".format(atoms.get_chemical_formula()[:15],
                                        atoms.info.get('uid', '0'))

        # Write contents of tar file
        tar_fullpath = path.join(workdir, tar_name)

        if not path.exists(path.dirname(tar_fullpath)):
            os.makedirs(path.dirname(tar_fullpath))
        # Overwrites everything -- expected behaviour
        # TODO: option for no overwrite?

        with open(tar_fullpath, 'wb') as original_file:
            original_file.write(b64decode(contents))

        return 1
