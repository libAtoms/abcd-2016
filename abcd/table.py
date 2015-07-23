__author__ = 'Patrick Szmucer'

from util import atoms2plaindict
from ase.utils import hill
from prettytable import PrettyTable
import time

class Table(object):
    '''
    Class that holds a list of dictionaries (created from the Atoms object).
    '''

    skip_cols = ['positions', 'forces', 'pbc', 'numbers', 'cell', 'stress', 'm_time']

    def __init__(self, atoms_it):
        self.dicts = []
        for atoms in atoms_it:
            old_dict = atoms2plaindict(atoms)
            
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

    def _format_value(self, key, value, max_len, force=False):
        if key == 'c_time' or key == 'm_time':
            value = time.strftime('%d%b%y %H:%M', time.localtime(value))
            max_len = 13
        elif key == 'uid':
            max_len = 15
        return self._trim(str(value), max_len)

    def print_rows(self):
        keys_list = self.keys_union()

        # Reorder the list
        order = ['uid', 'c_time', 'm_time', 'formula', 'n_atoms', 'config_type', 'calculator', 
                    'calculator_parameters', 'positions', 'energy', 'stress', 
                    'forces', 'pbc', 'numbers']
        for key in reversed(order):
            if key in keys_list:
                keys_list.insert(0, keys_list.pop(keys_list.index(key)))

        t = PrettyTable([self._trim(key, 10) for key in keys_list if key not in self.skip_cols])
        t.padding_width = 0
        no_rows = 0
        for dct in self.dicts:
            lst = []
            for key in keys_list:
                if key in self.skip_cols:
                    continue
                if key in dct:
                    value = self._format_value(key, dct[key], 6)
                else:
                    value = '-'
                lst.append(value)
            t.add_row(lst)
            no_rows += 1

        s = ''
        if no_rows > 0:
            s += t.get_string()
            s += '\n  Not displaying: {}\n'.format(self.skip_cols)
        s += '  Rows: {}'.format(no_rows)
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

    def keys_union(self):
        keys = set()
        for dct in self.dicts:
            for key in dct:
                keys.add(key)
        return sorted(list(keys))

    def keys_intersection(self):
        if self.dicts:
            keys = set(list(self.dicts[0].keys()))
        else:
            return set()
        for dct in self.dicts[1:]:
            new_keys = set()
            for key in dct:
                new_keys.add(key)
            keys = keys & new_keys
        return sorted(list(keys))

    def print_keys_table(self):
        union = self.keys_union()
        intersection = self.keys_intersection()
        ranges = {key: self.values_range(key) for key in union}

        t_intersection = PrettyTable(['Key', 'Min', 'Max'])
        t_intersection.padding_width = 0
        t_intersection.align["Key"] = "l"

        print '\nINTERSECTION:'
        for key in intersection:
            row = [key, self._format_value(key, ranges[key][0], 18), 
                        self._format_value(key, ranges[key][1], 18)]
            t_intersection.add_row(row)
        print t_intersection

        t_union = PrettyTable(['Key', 'Min', 'Max'])
        t_union.padding_width = 0
        t_union.align["Key"] = "l"

        print '\nUNION:'
        for key in union:
            row = [key, self._format_value(key, ranges[key][0], 18), 
                        self._format_value(key, ranges[key][1], 18)]
            t_union.add_row(row)
        print t_union
