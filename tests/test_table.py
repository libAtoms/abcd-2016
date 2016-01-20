"""
Simple unit tests for abcd.table
"""

from abcd.table import trim

class TestTrim:

    def test_nocut_equal(self):
        assert trim('', 0) == ''
        assert trim('string', 6) == 'string'

    def test_nocut_larger(self):
        assert trim('string', 7) == 'string'

    def test_nocut_negative(self):
        assert trim('string', -1) == 'string'

    def test_negative(self):
        assert trim('string', -7) == '..'

    def test_cut(self):
        assert trim('string', 3) == 'str..'

    def test_cut_zero(self):
        assert trim('string', 0) == '..'

    def test_integer_nocut(self):
        assert trim(12345, 5) == '12345'

    def test_integer_cut(self):
        assert trim(12345678, 5) == '12345..'

