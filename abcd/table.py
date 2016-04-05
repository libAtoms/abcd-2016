from __future__ import print_function

import collections
import time

from prettytable import PrettyTable

from abcd.util.atoms import atoms2dict, filter_keys

__author__ = 'Patrick Szmucer'


def trim(val, length):
    '''Trim the string if it's longer than "length" (and add dots at the end)'''
    s = str(val)
    if length == -1 or (len(s) <= length+1):
        return s
    else:
        return (s[:length] + '..')


def atoms_list2dict(atoms_it):
    '''Converts an Atoms iterator into a plain, one-level-deep list of dicts'''
    dicts = []
    for atoms in atoms_it:
        dct = atoms2dict(atoms, plain_arrays=True)
        if 'info' in dct and dct['info']:
            for key, value in dct['info'].items():
                dct[key] = dct['info'][key]
        if 'arrays' in dct and dct['arrays']:
            for key, value in dct['arrays'].items():
                dct[key] = dct['arrays'][key]
        dct.pop('info', None)
        dct.pop('arrays', None)
        dicts.append(dct)
    return dicts


def format_value(value, key):
    '''Applies special formatting for some key-value pairs'''
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
    elif key == 'original_files' or key == 'original_file_contents':
        v = '<file>'
    return v


def print_kvps(kvps):
    '''Takes a list of tuples, where each tuple is a key-value pair, and
        prints it.'''
    try:
        max_k = max(len(t[0]) for t in kvps)
    except ValueError:
        print('  -\n')
        return

    s = ''
    for t in kvps:
        if t[1] is None:
            continue
        s += '  ' + str(t[0]).ljust(max_k)
        s += ':  '
        s += str(format_value(t[1], t[0]))
        s += '\n'
    print(s)


def print_rows(atoms_list, border=True, truncate=True, show_keys=[], omit_keys=[]):
    '''Prints a full table'''

    dicts = atoms_list2dict(atoms_list)
    if not dicts:
        print('  Nothing to display')
        return

    keys = set()
    for dct in dicts:
        keys = keys | set(dct.keys())
    keys_list = list(keys)

    # Decide which keys to show/omit
    keys_list = filter_keys(keys_list, show_keys, omit_keys)

    # Reorder the list, but only if show_keys was []
    if not show_keys:
        order = ['uid', 'c_time', 'formula', 'n_atoms', 'numbers',
            'config_type', 'pbc', 'positions', 'cell', 'stress', 'forces',
            'energy', 'calculator', 'calculator_parameters']
        for key in reversed(order):
            if key in keys_list:
                keys_list.insert(0, keys_list.pop(keys_list.index(key)))

    if not keys_list:
        print('  No keys to display')
        return

    if truncate:
        max_title_len = 10
        max_cell_len = 8
    else:
        max_title_len = 100
        max_cell_len = 100

    # Initialise the table
    headers = []
    for key in keys_list:
        headers.append(trim(key, max_title_len))
    t = PrettyTable(headers)
    if border:
        t.padding_width = 0
        t.border = True
    else:
        t.padding_width = 1
        t.border = False
        t.align = 'l'

    # Apply special size rules to some keys
    cell_sizes = {}
    for key in keys_list:
        if not truncate:
            cell_sizes[key] = max_cell_len
        if key == 'uid':
            cell_sizes[key] = 16
        elif key in ['c_time', 'm_time']:
            cell_sizes[key] = 13
        else:
            cell_sizes[key] = max_cell_len

    # Populate the table with rows
    no_rows = 0
    for dct in dicts:
        lst = []
        for key in keys_list:
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
    comment = '' if border else '#'

    if no_rows > 0:
        s += comment + t.get_string() + '\n'
    s += comment + '  Rows: {}'.format(no_rows)
    print(s)


def print_keys_table(atoms_list, border=True, truncate=True, show_keys=[], omit_keys=[]):
    '''Prints two tables: Intersection table and Union table, and shows min and max values
        for each key'''

    dicts = atoms_list2dict(atoms_list)
    if len(dicts) == 0:
        print('  Nothing to display')
        return

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

    intersection = filter_keys(intersection, show_keys, omit_keys)
    union = filter_keys(union, show_keys, omit_keys)

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

    if truncate:
        max_key_len = 50
        max_val_len = 40
    else:
        max_key_len = 100
        max_val_len = 100

    def table_string(lst):
        t = PrettyTable(['Key', 'Min', 'Max'])
        if border:
            t.padding_width = 0
            t.border = True
            t.align['Key'] = 'l'
        else:
            t.padding_width = 1
            t.border = False
            t.align = 'l'

        s = ''
        no_keys = 0
        for key in lst:
            k = '{} ({})'.format(trim(key, max_key_len), str(counter[key]))
            min_val = format_value(ranges[key][0], key)
            max_val = format_value(ranges[key][1], key)
            row = [k, trim(min_val, max_val_len),
                        trim(max_val, max_val_len)]
            t.add_row(row)
            no_keys += 1

        if no_keys != 0:
            s += t.get_string()
        else:
            s += '\nNo keys to display'
        return s

    comment = '' if border else '# '
    s = ''
    s += '\n' + comment + 'ROWS: {}'.format(len(dicts)) + '\n'
    s += '\n' + comment + 'INTERSECTION'
    s += '\n' + comment + table_string(intersection) + '\n'
    s += '\n' + comment + 'UNION'
    s += '\n' + comment + table_string(union)+ '\n'
    print(s)


def print_long_row(atoms):
    '''Prints full information about one configuration'''

    d = atoms2dict(atoms, True)
    info = d['info']
    arrays = d['arrays']

    # General information about the configuration
    print('')
    g = []
    g.append(('uid', info.pop('uid', None)))
    g.append(('c_time', info.pop('c_time', None)))
    print_kvps(g)

    # Formula and number of atoms
    g = []
    g.append(('formula', info.pop('formula', None)))
    g.append(('n_atoms', info.pop('n_atoms', None)))
    g.append(('numbers', d.pop('numbers', None)))
    print_kvps(g)

    # "Spatial" information
    g = []
    g.append(('config_type', info.pop('config_type', None)))
    g.append(('cell', d.pop('cell', None)))
    g.append(('positions', d.pop('positions', None)))
    g.append(('pbc', d.pop('pbc', None)))
    print_kvps(g)

    # Calculated properties
    g = []
    g.append(('energy', d.pop('energy', None)))
    g.append(('energy', info.pop('energy', None)))
    g.append(('stress', d.pop('stress', None)))
    g.append(('forces', d.pop('forces', None)))
    g.append(('masses', d.pop('masses', None)))
    print_kvps(g)

    # Other main information
    print('Other:')
    g = [(k, v) for k, v in d.items() if k not in ('info', 'arrays')]
    print_kvps(g)

    # Other kvps from the info array
    print('Other (info):')
    g = [(k, v) for k, v in info.items()]
    print_kvps(g)

    # Data from the arrays dict
    print('Other (arrays):')
    g = [(k, v) for k, v in arrays.items()]
    print_kvps(g)
