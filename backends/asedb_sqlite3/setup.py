__author__ = 'Patrick Szmucer'

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

setup(
    name='abcd_asedb_sqlite3',
    description='ASEdb SQLite3 backend for Atomic structure sharing framework',
    author='Patrick Szmucer',
    author_email='pjs87@cam.ac.uk',
    version='0.1.0',
    install_requires=['abcd'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Development Status:: 2 - Pre - Alpha"],
    entry_points={
        'console_scripts': [
            'abcd-asedb-server = asedb_sqlite3_backend.server:main',
            'abcd-asedb = asedb_sqlite3_backend.util:main'
        ],
    }
)