"""
Run external commands from inside pytest.
"""

import subprocess


def test_abcd():
    abcd_cmd = ['abcd']
    assert subprocess.check_call(abcd_cmd) == 0
