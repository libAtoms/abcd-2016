__author__ = 'Patrick Szmucer'

from util import atoms2dict
from ase.utils import hill
from prettytable import PrettyTable
import time
import collections
from numpy import linalg as LA
import numpy as np

def trim(val, length):
    s = str(val)
    if len(s) > length+1:
        return (s[:length] + '..')
    else:
        return s

def atoms_list2dict(atoms_it):
    dicts = []
    for atoms in atoms_it:
        dct = atoms2dict(atoms, plain_arrays=True)
        if 'info' in dct and dct['info']:
            for key, value in dct['info'].iteritems():
                dct[key] = dct['info'][key]
        if 'arrays' in dct and dct['arrays']:
            for key, value in dct['arrays'].iteritems():
                dct[key] = dct['arrays'][key]
        dct.pop('info', None)
        dct.pop('arrays', None)
        dicts.append(dct)
    return dicts

def format_value(value, key):
    v = value
    if key == 'c_time' or key == 'm_time':
        v = time.strftime('%d%b%y %H:%M', time.localtime(value))
    elif key == 'pbc':
        if isinstance(v, collections.Container):
            v = ''
            for a in value:
                v += 'T' if a else 'F'
        else:
            v += 'T' if value else 'F'
    return v

def print_rows(atoms_list, border=True, truncate=True):
    dicts = atoms_list2dict(atoms_list)
    keys = set()
    for dct in dicts:
        keys = keys | set(dct.keys())
    keys_list = list(keys)

    # Reorder the list
    order = ['uid', 'c_time', 'm_time', 'formula', 'n_atoms', 'numbers',
            'config_type', 'pbc', 'positions', 'cell', 'stress', 'forces',
            'energy', 'calculator', 'calculator_parameters']
    for key in reversed(order):
        if key in keys_list:
            keys_list.insert(0, keys_list.pop(keys_list.index(key)))

    # Overwrite "truncate" if "border" is False
    if not border:
        truncate = False
    if truncate:
        max_title_len = 10
        max_cell_len = 8
    else:
        max_title_len = 16
        max_cell_len = 16

    # Initialise the table
    skip_cols = ['numbers', 'm_time', 'original_file_contents']
    t = PrettyTable([trim(key, max_title_len) for key in keys_list if key not in skip_cols])
    if border:
        t.padding_width = 0
        t.border = True
    else:
        t.padding_width = 1
        t.border = False
        t.align = 'l'
    
    cell_sizes = {}
    for key in keys_list:
        if key == 'uid':
            cell_sizes[key] = 16
        elif key in ['c_time', 'm_time']:
            cell_sizes[key] = 13
        else:
            cell_sizes[key] = max_cell_len

    # Populate the table with rows
    no_rows = 0
    not_displaying = set()
    for dct in dicts:
        lst = []
        for key in keys_list:
            if key in skip_cols:
                not_displaying.add(key)
                continue
            if key in dct:
                value = format_value(dct[key], key)
                value = trim(value, cell_sizes[key])
            else:
                value = '-'
            lst.append(value)
        t.add_row(lst)
        no_rows += 1

    # Print the table
    s = ''
    if not border:
        comment = '#'
    else:
        comment = ''

    if no_rows > 0:
        s += comment + t.get_string()
        s += '\n' + comment + '  Not displaying: {}\n'.format(list(not_displaying))
    s += comment + '  Rows: {}'.format(no_rows)
    print s

def print_keys_table(atoms_list):

    dicts = atoms_list2dict(atoms_list)

    union = set()
    intersection = set(dicts[0].keys())
    counter = collections.Counter()
    for dct in dicts:
        keys = set(dct.keys())
        counter.update(keys)
        union = union | keys
        intersection = intersection & keys
    intersection = sorted(list(intersection))
    union = sorted(list(union))

    ranges = {}
    for key in union:
        # Find the minimum for this key
        values = []
        for dct in dicts:
            if key in dct:
                values.append(dct[key])
        try:
            rang = (min(values), max(values))
        except:
            rang = ('...', '...')
        ranges[key] = rang

    def print_table(lst, title):
        t = PrettyTable(['Key', 'Min', 'Max'])
        t.padding_width = 0
        t.align['Key'] = 'l'
        print '\n', title
        for key in lst:
            k = '{} ({})'.format(trim(key, 25), str(counter[key]))
            row = [k, trim(ranges[key][0], 18),
                        trim(ranges[key][1], 18)]
            t.add_row(row)
        print t

    print '\nROWS:', len(dicts)
    print_table(intersection, 'INTERSECTION')
    print_table(union, 'UNION')
