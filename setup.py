import os
from setuptools import setup

# Utility function to read the README file.


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="pysystemtrade",
    version="0.0.1",
    author="Robert Carver",
    description=("Python framework for running systems as in Robert Carver's book Systematic Trading"
                 " (www.systematictrading.org)"),
    license="GNU GPL v3",
    keywords="systematic trading interactive brokers",
    url="http://qoppac.blogspot.co.uk/p/pysystemtrade.html",
    packages=['examples', 'syscore', 'sysdata', 'systems', 'syssims'],
    long_description=read('README.md'),
    install_requires=["pandas >= 0.17.0", "numpy >= 1.10.1", "python >= 3.4.3", "matlotplib > 1.4.3",
                      "yaml > 3.11"],
    extras_require=dict(),
    include_package_data=True
)
