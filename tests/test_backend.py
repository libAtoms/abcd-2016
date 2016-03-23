"""
Testing the abstract base class of the backend.

"""

import pytest

from abcd import backend


def test_abc_backend():
    """Can't instance ABC."""
    with pytest.raises(TypeError) as excinfo:
        b = backend.Backend()
    assert "Can't instantiate abstract class" in str(excinfo.value)


def test_abc_cursor():
    """Can't instance ABC."""
    with pytest.raises(TypeError) as excinfo:
        b = backend.Cursor()
    assert "Can't instantiate abstract class" in str(excinfo.value)


def test_backend_implemented():
    """Can instance once all methods are implemented."""
    class Implemented(backend.Backend):
        def add_keys(self, *args, **kwargs):
            pass

        def authenticate(self, *args, **kwargs):
            pass

        def close(self, *args, **kwargs):
            pass

        def find(self, *args, **kwargs):
            pass

        def insert(self, *args, **kwargs):
            pass

        def is_open(self, *args, **kwargs):
            pass

        def list(self, *args, **kwargs):
            pass

        def open(self, *args, **kwargs):
            pass

        def remove(self, *args, **kwargs):
            pass

        def remove_keys(self, *args, **kwargs):
            pass

        def update(self, *args, **kwargs):
            pass
    # making an instance works now
    ib = Implemented()
    assert isinstance(ib, backend.Backend)


def test_cursor_implemented():
    """Can instance once all methods are implemented."""
    class Implemented(backend.Cursor):
        def next(self, *args, **kwargs):
            pass

        def count(self, *args, **kwargs):
            pass

    ic = Implemented()
    assert isinstance(ic, backend.Cursor)
