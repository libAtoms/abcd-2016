__author__ = 'Patrick Szmucer'

'''
QUERYING CONVENTION
Query is a list of the Condition objects. Each Condition object specifies
the following:
- key - a key that will be searched. Searchable Atoms properties are all
		properties contained in the Atoms object and Atoms.info dictionary. 
		Arrays are not searchable. A number of additional keys which are 
		not directly stored in the atoms object can be specified. These 
		are specified below as "additional_keys".
- operator - one of:
	'=' - equal
	'!=' - not equal
	'>' - greater
	'>=' - greater or equal
	'<' - less
	'<=' - less or equal
	'~' - contains
- operand - LogicalList, which is a list of items linked by and/or.

This list of queries is sent to the backend which then interprets it.
'''

operators = ['=', '!=', '>', '>=', '<', '<=', '~']
additional_keys = ['formula', 'natoms']

class LogicalList(object):
	'''
	List of items linked by a logical operator
	"and" or "or".
	'''

	linking_operators = ['and', 'or']

	def __init__(self, operator, lst):
		'''
		:param string operator: One of and/or
		:param list lst: list of items
		'''
		if operator not in self.linking_operators:
			raise RuntimeError('Unsupported operator {}'.format(operator))
		self.linking_operator = operator
		self.list = lst

	def __str__(self):
		return '{}{}'.format(self.linking_operator.upper(), self.list)

def And(*args):
	return LogicalList('and', args)

def Or(*args):
	return LogicalList('or', args)

class Condition(object):
	def __init__(self, key, operator, operand):
		'''
		:param key: LHS of the condition (key)
		:type key: string
		:param operator: operator
		:type operator: string
		:param rhs: RHS of the operator
		:type rhs: list of strings/numbers
		'''
		if operator in operators:
			self.operator = operator
		else:
			raise RuntimeError('Unknown operator {}'.format(operator))
		self.operand = operand
		self.key = key

	def __str__(self):
		return '{} {} {}'.format(self.key, self.operator, self.operand)

class QueryTranslator(object):
	def __init__(self, *args):
		'''
		:param *args: list of individual queries or string of queries 
					separated by spaces.
		'''
		queries = []
		for arg in args:
			queries += arg.split(' ')
		self.queries = queries
	
	def translate(self):
		'''
		Translates from the CLI query language to
		a list of conditions.

		:return: Returns a list of conditions
		:rtype: list
		'''
		operators.sort(key=len, reverse=True)
		conditions = []

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

		def interpret(query, operator):
			key, vals = query.split(op)
			vals = vals.split(',')
			for i, v in enumerate(vals):
				if is_int(v):
					vals[i] = int(v)
				elif is_float(v):
					vals[i] = float(v)
			if operator == '!=':
				Link = And
			else:
				Link = Or
			c = Condition(key, op, Link(*vals))
			conditions.append(c)

		for query in self.queries:
			valid_query = False
			for op in operators:
				if op in query:
					interpret(query, op)
					valid_query = True
					break
			if not valid_query:
				raise RuntimeError('Invalid query: {}'.format(query))

		return conditions