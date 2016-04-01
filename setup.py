# Require setuptools for entry_points and find_packages

from setuptools import setup, find_packages

setup(
    name='abcd',
    description='Atomic structure sharing framework',
    author='Martin Uhrin, Patrick Szmucer',
    author_email='martin.uhrin@epfl.ch, pjs87@cam.ac.uk',
    version='0.1.0',
    install_requires=[
        'prettytable',  # CLI output in tables
        'numpy',  # Array data is numpy arrays
        'six',  # Compatibility with python 2
        'ase>=3.10.0',  # Atom data are ase.Atoms,
        'appdirs',  # Makes cross platform config and data files easier
    ],
    tests_require=['pytest'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Development Status:: 2 - Pre - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Database :: Front-Ends",
        "Topic :: Scientific/Engineering"],
    entry_points={
        'console_scripts': [
            'abcd = abcd.cli:main',
        ],
    }
)
