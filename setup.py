

import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

setup(
    name='abcd',
    description='Atomic structure sharing framework',
    author='Martin Uhrin, Patrick Szmucer',
    author_email='martin.uhrin@epfl.ch, pjs87@cam.ac.uk',
    version='0.0.0',
    install_requires=['prettytable', 'numpy'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Development Status:: 2 - Pre - Alpha"],
    entry_points={
        'console_scripts': [
            'abcd = abcd.cli:main',
        ],
    }
)

ase_link = 'https://wiki.fysik.dtu.dk/ase/download.html#latest-development-release'
try:
    from ase.svnversion import svnversion
except:
    print '\nInstall the development version of ASE from', ase_link
else:
    if svnversion.split(':')[-1] < '4590':
        print '\nMinimum supported ASE version is r4590. You can install the development version of ASE from', ase_link