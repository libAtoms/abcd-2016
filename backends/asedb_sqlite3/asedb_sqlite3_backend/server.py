__author__ = 'Patrick Szmucer'

'''
Response codes:
201: b64encoded string
202: json and b64encoded list
203: json and b64encoded dictionary
204: json and b64encoded list of dictionaries
220: json and b64encoded InsertResult dictionary
221: json and b64encoded UpdateResult dictionary
222: json and b64encoded RemoveResult dictionary
223: json and b64encoded AddKvpResult dictionary
224: json and b64encoded RemoveKeysResult dictionary
'''

import argparse
import asedb_sqlite3_backend as backend
import json
import sys
from abcd.structurebox import StructureBox
from abcd.util import dict2atoms, atoms2dict
from asedb_sqlite3_backend import ASEdbSQlite3Backend as Backend
from base64 import b64encode, b64decode


def main():
	# Get the username
	#
	try:
		user = sys.argv[1]
	except:
		print 'No user specified'
		return
	try:
		arguments = sys.argv[2:]
	except:
		arguments = []

	# Initialise the parser
	#
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers(dest='subparser_name')

	list_parser = subparsers.add_parser('list')

	insert_parser = subparsers.add_parser('insert')
	insert_parser.add_argument('database')
	insert_parser.add_argument('atoms')

	update_parser = subparsers.add_parser('update')
	update_parser.add_argument('database')
	update_parser.add_argument('atoms')
	update_parser.add_argument('--upsert', action='store_true', default=False)
	update_parser.add_argument('--replace', action='store_true', default=False)

	remove_parser = subparsers.add_parser('remove')
	remove_parser.add_argument('database')
	remove_parser.add_argument('filter')
	remove_parser.add_argument('--just-one', action='store_true', default=False)

	find_parser = subparsers.add_parser('find')
	find_parser.add_argument('database')
	find_parser.add_argument('filter')
	find_parser.add_argument('--sort', default=None)
	find_parser.add_argument('--reverse', action='store_true', default=False)
	find_parser.add_argument('--limit', type=int, default=0)
	find_parser.add_argument('--keys', default='++')
	find_parser.add_argument('--omit-keys', default=[])

	add_keys_parser = subparsers.add_parser('add-keys')
	add_keys_parser.add_argument('database')
	add_keys_parser.add_argument('filter')
	add_keys_parser.add_argument('kvp')

	remove_keys_parser = subparsers.add_parser('remove-keys')
	remove_keys_parser.add_argument('database')
	remove_keys_parser.add_argument('filter')
	remove_keys_parser.add_argument('keys')

	args = parser.parse_args(arguments)

	# Define actions
	if args.subparser_name == 'list':
		box = StructureBox(Backend(user=user))
		dbs = box.list('')
		print '202:' + b64encode(json.dumps(dbs))

	elif args.subparser_name == 'insert':
		box = StructureBox(Backend(database=args.database, user=user))
		atoms_dcts_list = json.loads(b64decode(args.atoms))
		atoms_list = [dict2atoms(atoms_dct, plain_arrays=True) for atoms_dct in atoms_dcts_list]
		res = box.insert('', atoms_list)
		print '220:' + b64encode(json.dumps(res.__dict__))

	elif args.subparser_name == 'update':
		box = StructureBox(Backend(database=args.database, user=user))
		atoms_dcts_list = json.loads(b64decode(args.atoms))
		atoms_list = [dict2atoms(atoms_dct, plain_arrays=True) for atoms_dct in atoms_dcts_list]
		res = box.update('', atoms_list, 
							args.upsert, 
							args.replace)
		print '221:' + b64encode(json.dumps(res.__dict__))

	elif args.subparser_name == 'remove':
		box = StructureBox(Backend(database=args.database, user=user))
		query = json.loads(b64decode(args.filter))
		res = box.remove('', query, 
							args.just_one)
		print '222:' + b64encode(json.dumps(res.__dict__))
		
	elif args.subparser_name == 'find':
		box = StructureBox(Backend(database=args.database, user=user))
		atoms_it = box.find('', json.loads(b64decode(args.filter)),
								json.loads(b64decode(args.sort)), 
								args.reverse, 
								args.limit, 
								json.loads(b64decode(args.keys)), 
								json.loads(b64decode(args.omit_keys)))
		atoms_dcts_list = [atoms2dict(atoms, True) for atoms in atoms_it]
		print '204:' + b64encode(json.dumps(atoms_dcts_list))

	elif args.subparser_name == 'add-keys':
		box = StructureBox(Backend(database=args.database, user=user))
		res = box.add_keys('', json.loads(b64decode(args.filter)), 
								json.loads(b64decode(args.kvp)))
		print '223:' + b64encode(json.dumps(res.__dict__))

	elif args.subparser_name == 'remove-keys':
		box = StructureBox(Backend(database=args.database, user=user))
		res = box.remove_keys('', json.loads(b64decode(args.filter)), 
									json.loads(b64decode(args.keys)))
		print '224:' + b64encode(json.dumps(res.__dict__))