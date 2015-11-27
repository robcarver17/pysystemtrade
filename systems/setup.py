import os
from setuptools import setup

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "an_example_pypi_project",
    version = "0.0.1",
    author = "Robert Carver",
    description = ("An demonstration of how to create, document, and publish "
                                   "to the cheese shop a5 pypi.org."),
    license = "BSD",
    keywords = "backtesting trading systematic ",
    url = "qoppac.blogspot.com/code.html",
    packages=['examples', 'syscore', 'sysdata', 'syssims', 'systems'],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Topic :: Utilities",
        "License ::  GPL 3.0 License",
    ],
)