__author__ = 'Martin Uhrin'


#import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

setup(
    name='abcd_mongodb',
    description='MongoDB backend for Atomic structure sharing framework',
    author='Martin Uhrin',
    author_email='martin.uhrin@epfl.ch',
    version='0.0.0',
    install_requires=['abcd', 'ase', 'pymongo'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Development Status:: 2 - Pre - Alpha"],
)

