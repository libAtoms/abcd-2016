# Testing

A test suite is supplied to ensure the functionality of abcd and prevent
regressions.

## Setup

Tests are designed for `pytest`. Execute `py.test` in the root directory to
run the tests.

Tests that modify files and databases are restricted to run only on Travis
systems.
