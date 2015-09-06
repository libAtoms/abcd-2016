"""
Interface for the ASEdb backend. Its purpose is to be triggered
by the communicate_with_remote function from remote.py, 
communicate with the ASEdb backend and print results/data
to standard output. The output is b64-encoded and should be in 
a form XYZ:OUTPUT, where XYZ is the response code which indicates
what type of output was produced (see below).

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
400: b64encoded string - Error
401: b64encoded string - ReadError
402: b64encoded string - WriteError
"""

__author__ = 'Patrick Szmucer'

import argparse
import asedb_sqlite3_backend as backend
import json
import sys
from abcd.backend import ReadError, WriteError
from abcd.structurebox import StructureBox
from abcd.util import dict2atoms, atoms2dict
from asedb_sqlite3_backend import ASEdbSQlite3Backend as Backend
from base64 import b64encode, b64decode


def error_handler(func):
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ReadError as e:
            print '401:' + b64encode(str(e))
        except WriteError as e:
            print '402:'+ b64encode(str(e))
        except:
            print '400:' + b64encode(str(e))
    return func_wrapper


@error_handler
def backendList(user):
    box = StructureBox(Backend(user=user))
    dbs = box.list('')
    print '202:' + b64encode(json.dumps(dbs))


@error_handler
def backendInsert(database, user, atoms):
    box = StructureBox(Backend(database=database, user=user))
    atoms_dcts_list = json.loads(b64decode(atoms))
    atoms_list = [dict2atoms(atoms_dct, plain_arrays=True) for atoms_dct in atoms_dcts_list]
    res = box.insert('', atoms_list)
    print '220:' + b64encode(json.dumps(res.__dict__))


@error_handler
def backendUpdate(database, user, atoms, upsert, replace):
    box = StructureBox(Backend(database=database, user=user))
    atoms_dcts_list = json.loads(b64decode(atoms))
    atoms_list = [dict2atoms(atoms_dct, plain_arrays=True) for atoms_dct in atoms_dcts_list]
    res = box.update('', atoms_list, 
                    upsert, 
                    replace)
    print '221:' + b64encode(json.dumps(res.__dict__))


@error_handler
def backendRemove(database, user, filter, just_one):
    box = StructureBox(Backend(database=database, user=user))
    query = json.loads(b64decode(filter))
    res = box.remove('', query, 
                    just_one)
    print '222:' + b64encode(json.dumps(res.__dict__))


@error_handler
def backendFind(database, user, filter, sort, reverse, limit, keys, omit_keys):
    box = StructureBox(Backend(database=database, user=user))
    atoms_it = box.find('', json.loads(b64decode(filter)),
                        json.loads(b64decode(sort)), 
                        reverse, limit, 
                        json.loads(b64decode(keys)), 
                        json.loads(b64decode(omit_keys)))
    atoms_dcts_list = [atoms2dict(atoms, True) for atoms in atoms_it]
    print '204:' + b64encode(json.dumps(atoms_dcts_list))


@error_handler
def backendAddKeys(database, user, filter, kvp):
    box = StructureBox(Backend(database=database, user=user))
    res = box.add_keys('', json.loads(b64decode(filter)), 
                        json.loads(b64decode(kvp)))
    print '223:' + b64encode(json.dumps(res.__dict__))


@error_handler
def backendRemoveKeys(database, user, filter, keys):
    box = StructureBox(Backend(database=database, user=user))
    res = box.remove_keys('', json.loads(b64decode(filter)), 
                            json.loads(b64decode(keys)))
    print '224:' + b64encode(json.dumps(res.__dict__))


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

    try:
        if args.database == 'None':
            args.database = None
    except AttributeError:
        pass

    # Define actions
    if args.subparser_name == 'list':
        backendList(user)

    elif args.subparser_name == 'insert':
        backendInsert(args.database, user, args.atoms)

    elif args.subparser_name == 'update':
        backendUpdate(args.database, user, args.atoms, args.upsert, args.replace)

    elif args.subparser_name == 'remove':
        backendRemove(args.database, user, args.filter, args.just_one)
        
    elif args.subparser_name == 'find':
        backendFind(args.database, user, args.filter, args.sort, 
                    args.reverse, args.limit, args.keys, args.omit_keys)

    elif args.subparser_name == 'add-keys':
        backendAddKeys(args.database, user, args.filter, args.kvp)

    elif args.subparser_name == 'remove-keys':
        backendRemoveKeys(args.database, user, args.filter, args.keys)
