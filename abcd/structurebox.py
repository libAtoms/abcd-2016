

__author__ = 'Martin Uhrin'

class StructureBox(object):

    class BackendOpen:
        def __init__(self, backend):
            self.backend = backend
            self.did_open = False

        def __enter__(self):
            if not self.backend.is_open:
                self.backend.open()
                self.did_open = True
            return self.backend

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.did_open:
                self.backend.close()
                self.did_open = False

    def __init__(self, backend):
        self.backend = backend

    def list(self, auth_token):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.list(auth_token)

    def authenticate(self, credentials):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.authenticate(credentials)

    def insert(self, auth_token, atoms):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.insert(auth_token, atoms)

    def update(self, auth_token, atoms, upsert=False, replace=False):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.update(auth_token, atoms, upsert, replace)

    def find(self, auth_token, filter, sort={}, limit=0, keys=None, omit_keys=False):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.find(auth_token, filter, sort, limit, keys, omit_keys)

    def remove(self, auth_token, filter, just_one=True):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.remove(auth_token, filter, just_one)

    def add_keys(self, auth_token, filter, kvp):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.add_keys(auth_token, filter, kvp)

    def remove_keys(self, auth_token, filter, keys):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.remove_keys(auth_token, filter, keys)