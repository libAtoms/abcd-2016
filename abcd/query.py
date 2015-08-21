__author__ = 'Patrick Szmucer'

import shlex
from ase.data import chemical_symbols

# This is a list of operators that can be used on the command line
operators = ['=', '!=', '>', '>=', '<', '<=', '~']

class QueryError(Exception):
	def __init__(self, message):
		super(QueryError, self).__init__(message)

def is_float(n):
	try:
		n = float(n)
	except ValueError:
		return False
	else:
		return True

def is_int(n):
	try:
		a = int(n)
		b = float(n)
	except ValueError:
		return False
	else:
		return a == b

def elements2numbers(elements):
	for i, v in enumerate(elements):
		try:
			elements[i] = chemical_symbols.index(elements[i])
		except ValueError:
			raise QueryError('Unknown element: {}'.format(elements[i]))

def interpret(query):
	'''Translates a single query to the MongoDB format'''

	# Find the operator
	operator = None
	for op in operators:
		if op in query:
			operator = op

	if operator is None:
		raise QueryError(query)

	key, vals = query.split(operator)
	vals = vals.split(',')

	if len(vals) == 0 or '' in vals:
		raise QueryError(query)

	# Convert strings representing numbers to numbers
	for i, v in enumerate(vals):
		if is_int(v):
			vals[i] = int(v)
		elif is_float(v):
			vals[i] = float(v)

	dct = {}
	if operator == '=' and len(vals) == 1:
		dct[key] = {'$eq': vals[0]}
	elif operator == '=':
		dct[key] = {'$in': vals}
	elif operator == '!=' and len(vals) == 1:
		dct[key] = {'$ne': vals[0]}
	elif operator == '!=':
		dct[key] = {'$nin': vals}
	elif operator == '>' and len(vals) == 1:
		dct[key] = {'$gt': vals[0]}
	elif operator == '>':
		raise QueryError(query)
	elif operator == '>=' and len(vals) == 1:
		dct[key] = {'$gte': vals[0]}
	elif operator == '>=':
		raise QueryError(query)
	elif operator == '<' and len(vals) == 1:
		dct[key] = {'$lt': vals[0]}
	elif operator == '<':
		raise QueryError(query)
	elif operator == '<=' and len(vals) == 1:
		dct[key] = {'$lte': vals[0]}
	elif operator == '<=':
		raise QueryError(query)
	elif operator == '~':
		# Searching will be done on the 'numbers' array
		if key == 'elements':
			key = 'numbers'
			elements2numbers(vals)
		dct[key] = {'$in': vals}
	else:
		raise QueryError(query)

	return dct

def update(d1, d2):
	'''Update dictionary d1 with d2'''
	for k, v in d2.iteritems():
		if k in d1:
			for op in d2[k].keys():
				if op in d1[k]:
					d1[k][op] += d2[k][op]
				else:
					d1[k].update(d2[k])
		else:
			d1[k] = v

def translate(queries_lst):
	'''Translates a list of queries to the MongoDB format'''

	# Pre-process the queries. Take care to not split key values
	# with spaces in them.
	queries = []
	for q in queries_lst:
		# Check the number of operators in the query.
		n = sum([q.count(op) for op in operators]) - sum(q.count(op) for op in ['!=', '>=', '<='])
		if n > 1:
			queries += shlex.split(q)
		else:
			queries.append(q)

	mongodb_query = {'$and': []}
	for query in queries:
		mongodb_query['$and'].append(interpret(query))
	return mongodb_query
