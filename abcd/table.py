__author__ = 'Patrick Szmucer'

from util import atoms2dict
from ase.utils import hill
from prettytable import PrettyTable
import time
from collections import Counter

class Table(object):
    '''
    Class that holds a list of dictionaries (created from the Atoms object).
    '''

    skip_cols = ['positions', 'forces', 'pbc', 'numbers', 'cell', 'stress', 'm_time']

    def __init__(self, atoms_it):
        self.dicts = []
        for atoms in atoms_it:
            old_dict = atoms2dict(atoms, plain_arrays=True)
            
            new_dict = dict(old_dict)
            new_dict.pop('info', None)
            new_dict.pop('arrays', None)

            if old_dict['info']:
                for key, value in old_dict['info'].iteritems():
                    new_dict[key] = old_dict['info'][key]

            self.dicts.append(new_dict)

    def _trim(self, str, length):
        if len(str) > length:
            return (str[:length] + '..')
        else:
            return str

    def _format_value(self, key, value, max_len):
        if key == 'c_time' or key == 'm_time':
            value = time.strftime('%d%b%y %H:%M', time.localtime(value))
            max_len = 13
        elif key == 'uid':
            max_len = 15
        return self._trim(str(value), max_len)

    def print_rows(self, border=True, truncate=True):
        keys = set()
        for dct in self.dicts:
            keys = keys | set(dct.keys())
        keys_list = list(keys)

        # Reorder the list
        order = ['uid', 'c_time', 'm_time', 'formula', 'n_atoms', 'config_type', 'calculator', 
                    'calculator_parameters', 'positions', 'energy', 'stress', 
                    'forces', 'pbc', 'numbers']
        for key in reversed(order):
            if key in keys_list:
                keys_list.insert(0, keys_list.pop(keys_list.index(key)))

        # Overwrite "truncate" if "border" is False
        if not border:
            truncate = False

        if truncate:
            max_title_len = 10
            max_cell_len = 6
        else:
            max_title_len = 16
            max_cell_len = 16
        t = PrettyTable([self._trim(key, 10) for key in keys_list if key not in self.skip_cols])

        if border:
            t.padding_width = 0
            t.border = True
        else:
            t.padding_width = 1
            t.border = False
            t.align = 'l'

        no_rows = 0
        for dct in self.dicts:
            lst = []
            for key in keys_list:
                if key in self.skip_cols:
                    continue
                if key in dct:
                    value = self._format_value(key, dct[key], max_cell_len)
                else:
                    value = '-'
                lst.append(value)
            t.add_row(lst)
            no_rows += 1

        s = ''
        if not border:
            comment = '#'
        else:
            comment = ''

        if no_rows > 0:
            s += comment + t.get_string()
            s += '\n' + comment + '  Not displaying: {}\n'.format(self.skip_cols)
        s += comment + '  Rows: {}'.format(no_rows)
        print s

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

    def print_keys_table(self):
        if not self.dicts:
            print 'Database is empty'
            return

        print '\nROWS:', len(self.dicts)
        
        union = set()
        intersection = set(self.dicts[0].keys())
        counter = Counter()
        for dct in self.dicts:
            keys = set(dct.keys())
            counter.update(keys)
            union = union | keys
            intersection = intersection & keys
        intersection = sorted(list(intersection))
        union = sorted(list(union))

        ranges = {key: self.values_range(key) for key in union}

        def print_table(lst, title):
            t = PrettyTable(['Key', 'Min', 'Max'])
            t.padding_width = 0
            t.align['Key'] = 'l'
            print '\n', title
            for key in lst:
                k = '{} ({})'.format(self._trim(key, 25), str(counter[key]))
                row = [k, self._format_value(key, ranges[key][0], 18), 
                            self._format_value(key, ranges[key][1], 18)]
                t.add_row(row)
            print t

        print_table(intersection, 'INTERSECTION')
        print_table(union, 'UNION')
