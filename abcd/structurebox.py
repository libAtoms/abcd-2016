

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

    def authenticate(self, credentials):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.authenticate(credentials)

    def insert(self, auth_token, atoms):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.insert(auth_token, atoms)

    def find(self, auth_token, filter):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.find(auth_token, filter)

    def remove(self, auth_token, filter, just_one=True):
        with StructureBox.BackendOpen(self.backend):
            return self.backend.remove(auth_token, filter, just_one)