# Require setuptools for entry_points and find_packages

from setuptools import setup, find_packages

setup(
    name='abcd',
    description='Atomic structure sharing framework',
    author='Martin Uhrin, Patrick Szmucer',
    author_email='martin.uhrin@epfl.ch, pjs87@cam.ac.uk',
    version='0.1.0',
    install_requires=['prettytable', 'numpy'],
    tests_require=['pytest'],
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
    # all the 3.10 series use __version__ not svnversion
    from ase import __version__
except ImportError:
    print('\nInstall the development version of ASE from:')
    print(ase_link)
