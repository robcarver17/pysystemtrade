from __future__ import print_function
import os
import sys
import platform
from setuptools import setup, find_packages
from distutils.version import StrictVersion

if StrictVersion(platform.python_version()) < StrictVersion('3.4.3'):
    print(
        'pysystemtrade requires Python 3.4.3 or later. Exiting.',
        file=sys.stderr)
    sys.exit(1)


def read(fname):
    '''Utility function to read the README file.'''
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="pysystemtrade",
    version="0.0.1",
    author="Robert Carver",
    description=
    ("Python framework for running systems as in Robert Carver's book Systematic Trading"
     " (www.systematictrading.org)"),
    license="GNU GPL v3",
    keywords="systematic trading interactive brokers",
    url="http://qoppac.blogspot.co.uk/p/pysystemtrade.html",
    packages=find_packages() + ['systems'],
    long_description=read('README.md'),
    install_requires=[
        "pandas >= 0.19.0", "numpy >= 1.10.1", "matplotlib > 1.4.3",
        "PyYAML>=3.11", "scipy>=0.17"
    ],
    tests_requires=['nose', 'flake8'],
    extras_require=dict(),
    test_suite='nose.collector',
    include_package_data=True)
