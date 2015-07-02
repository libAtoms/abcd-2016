from abcd import util, results

__author__ = 'Martin Uhrin'

import numpy as np
from pymongo import MongoClient
from pymongo.son_manipulator import SONManipulator
import ase.atoms
import ase.db.row

from abcd.backend import Backend
import abcd.authentication as authentication
import abcd.backend
import abcd.results as results
import abcd.util as util


class MongoDBBackend(Backend):
    class Transform(SONManipulator):
        def transform_incoming(self, son, collection):
            for (key, value) in son.items():
                if isinstance(value, np.ndarray):
                    son[key] = {"_type": "nparray", "value": value.tolist()}
                elif isinstance(value, dict):  # Make sure we recurse into sub-docs
                    son[key] = self.transform_incoming(value, collection)
            return son

        def transform_outgoing(self, son, collection):
            for (key, value) in son.items():
                if isinstance(value, dict):
                    if "_type" in value and value["_type"] == "nparray":
                        son[key] = np.array(value["value"])
                    else:  # Again, make sure to recurse into sub-docs
                        son[key] = self.transform_outgoing(value, collection)
            return son

    class Cursor(abcd.backend.Cursor):
        def __init__(self, pymongo_cursor):
            self.pymongo_cursor = pymongo_cursor

        def next(self):
            return ase.db.row.AtomsRow(self.pymongo_cursor.next()).toatoms()

        def count(self):
            return self.pymongo_cursor.count()

    def __init__(self, host, port, database='abcd', collection='structures',
                 user=None, password=None):
        super(MongoDBBackend, self).__init__()

        self.host = host
        self.port = port
        self.database_name = database
        self.collection_name = collection
        self.connection = MongoClient(self.host, self.port)
        self.db = self.connection[self.database_name]
        if user:
            self.db.authenticate(user, password)
        self.collection = self.db[self.collection_name]

        self.db.add_son_manipulator(MongoDBBackend.Transform())


    def authenticate(self, credentials):
        return authentication.AuthToken(credentials.username)

    def insert(self, auth_token, atoms):
        ids = []
        if isinstance(atoms, ase.atoms.Atoms):
            # We're just inserting one
            ids.append(self.collection.insert(util.atoms2dict(atoms)))
        else:
            # Assume atoms is an iterable
            dicts = [util.atoms2dict(a) for a in atoms]
            ids.extend(self.collection.insert(dicts))

        return results.InsertResult(ids)

    def remove(self, auth_token, filter, just_one):
        return results.RemoveResult(self.collection.remove(
            filter, multi=not just_one)["n"])

    def find(self, auth_token, filter):
        return MongoDBBackend.Cursor(self.collection.find(filter))

    def open(self):
        pass

    def close(self):
        pass

    def is_open(self):
        return True
