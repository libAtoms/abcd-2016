__author__ = 'Martin Uhrin'

from setuptools import setup, find_packages

setup(
    name='abcd_mongodb_backend',
    description='MongoDB backend for Atomic structure sharing framework',
    author='Martin Uhrin',
    author_email='martin.uhrin@epfl.ch',
    version='0.0.0',
    install_requires=['abcd', 'pymongo'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Development Status:: 2 - Pre - Alpha"],
)

