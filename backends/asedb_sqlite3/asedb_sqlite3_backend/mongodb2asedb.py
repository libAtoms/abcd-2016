from itertools import product
from ase.data import chemical_symbols

def interpret(key, op, val):
    # Returns a list of ASEdb queries, where elements in this list
    # are assumed to be ORed.
    queries = []
    if op == '$eq':
        queries.append('{}={}'.format(key, val))
    elif op == '$in':
        if key == 'numbers':
            if isinstance(val, list):
                for v in val:
                    queries.append(str(chemical_symbols[v]))
            else:
                queries.append(str(chemical_symbols[v]))
        else:
            if isinstance(val, list):
                for v in val:
                    queries.append('{}={}'.format(key, v))
            else:
                queries.append('{}={}'.format(key, v))
    elif op == '$ne':
        queries.append('{}!={}'.format(key, val))
    elif op == '$nin':
        queries.append(','.join(['{}!={}'.format(key, v) for v in val]))
    elif op == '$gt':
        queries.append('{}>{}'.format(key, val))
    elif op == '$gte':
        queries.append('{}>={}'.format(key, val))
    elif op == '$lt':
        queries.append('{}<{}'.format(key, val))
    elif op == '$lte':
        queries.append('{}<={}'.format(key, val))
    else:
        raise QueryError('{} {} {}'.format(key, op, val))

    return queries

def translate_query(query):
    '''Translates the MongoDB query to the ASEdb query'''

    asedb_queries = []
    for single_query in query['$and']:
        for key, dct in single_query.iteritems():
            for op, val in dct.iteritems():
                 asedb_queries.append(interpret(key, op, val))

    # Because ASEdb doesn't understand ORs, we need to split up
    # expressions with ORs into separate queries
    asedb_queries = list(product(*asedb_queries))
    return [','.join(lst) for lst in asedb_queries]