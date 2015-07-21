__author__ = 'Patrick Szmucer'

operators = ['=', '!=', '>', '>=', '<', '<=']

class Condition:
	def __init__(self, operator, operands):
		'''
		:param operator: operator
		:type operator: string
		:param operand: RHS of the operator
		:type operand: string/number or list of strings/numbers
		'''
		if operator in operators:
			self.operator = operator
		else:
			raise RuntimeError('Unknown operator {}'.format(operator))
		self.operands = operands

	def __str__(self):
		return '{} {}'.format(self.operator, self.operands)

class QueryTranslator(object):
	def __init__(self, *args):
		'''
		:param *args: list of individual queries
		'''
		self.queries = args
	
	def translate(self):
		'''
		Translates from the CLI query language to
		a dictonary of conditions.

		:return: Returns a dicitonary of key-conditions,
				where each condition specifies an operator
				(equal, less than, etc.) and 
				and operands.
		:rtype: dictionary
		'''
		operators.sort(key=len, reverse=True)
		query_dct = {}

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
			c = Condition(op, vals)
			if key in query_dct:
				query_dct[key].append(c)
			else:
				query_dct[key] = [c]

		for query in self.queries:
			for op in operators:
				if op in query:
					interpret(query, op)
					break

		return query_dct