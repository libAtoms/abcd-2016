"""
Unit tests for functions in the text utils.
"""

from abcd.util.text import filename_enumerator

class TestFilenameEnumerator:

    def test_no_numbers(self):
        fname = filename_enumerator('nope.xyz')
        assert fname == None

    def test_format_string(self):
        fname = filename_enumerator('yes_{}.xyz')
        assert fname is not None
        assert fname(7) == 'yes_7.xyz'

    def test_format_string_with_path(self):
        fname = filename_enumerator('{0}/yes_{0}.xyz')
        assert fname is not None
        assert fname(7) == '7/yes_7.xyz'

    def test_percent_format(self):
        fname = filename_enumerator('yes_%i.xyz')
        assert fname is not None
        assert fname(7) == 'yes_7.xyz'
