__author__ = 'Patrick Szmucer'

operators = ['=', '!=', '>', '>=', '<', '<=']

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
		:param *args: list of individual queries
		'''
		self.queries = args
	
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
			for op in operators:
				if op in query:
					interpret(query, op)
					break

		return conditions