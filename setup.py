from __future__ import print_function
import os
import sys
import platform
from setuptools import setup, find_packages
from distutils.version import StrictVersion

if StrictVersion(platform.python_version()) <= StrictVersion("3.10.0"):
    print("pysystemtrade requires Python 3.10.0 or later. Exiting.", file=sys.stderr)
    sys.exit(1)


def read(fname):
    """Utility function to read the README file."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def package_files(directory, extension="yaml"):
    paths = []
    for path, directories, filenames in os.walk(directory):
        for filename in filenames:
            if filename.split(".")[-1] == extension:
                paths.append(os.path.join("..", path, filename))

    return paths


def dir_this_file():
    return os.path.dirname(os.path.realpath(__file__))


private_dir = os.path.join(dir_this_file(), "private")
private_yaml_files = package_files(private_dir, "yaml")

provided_dir = os.path.join(dir_this_file(), "systems", "provided")
provided_yaml_files = package_files(provided_dir, "yaml")

control_dir = os.path.join(dir_this_file(), "syscontrol")
control_yaml_files = package_files(control_dir, "yaml")

data_csv_path = os.path.join(dir_this_file(), "data")
data_csv_files = package_files(data_csv_path, "csv")

init_csv_path = os.path.join(dir_this_file(), "sysinit")
init_csv_files = package_files(init_csv_path, "csv")

test_data_csv_path = os.path.join(dir_this_file(), "sysdata")
test_data_csv_files = package_files(test_data_csv_path, "csv")

default_config_path = os.path.join(dir_this_file(), "sysdata", "config")
default_config_yaml_files = package_files(default_config_path, "yaml")

brokers_csv_path = os.path.join(dir_this_file(), "sysbrokers")
brokers_csv_files = package_files(brokers_csv_path, "csv")

brokers_yaml_path = os.path.join(dir_this_file(), "sysbrokers")
brokers_yaml_files = package_files(brokers_yaml_path, "yaml")

package_data = {
    "": private_yaml_files
    + provided_yaml_files
    + data_csv_files
    + test_data_csv_files
    + brokers_csv_files
    + brokers_yaml_files
    + control_yaml_files
    + default_config_yaml_files
}

print(package_data)

setup(
    name="pysystemtrade",
    version="1.8.2",
    author="Robert Carver",
    description=(
        "Python framework for running systems as in Robert Carver's book Systematic Trading"
        " (https://www.systematicmoney.org/systematic-trading)"
    ),
    license="GNU GPL v3",
    keywords="systematic trading interactive brokers",
    url="https://qoppac.blogspot.com/p/pysystemtrade.html",
    packages=find_packages(),
    package_data=package_data,
    long_description=read("README.md"),
    install_requires=[
        "pandas==2.1.3",
        "matplotlib>=3.0.0",
        "ib-insync==0.9.86",
        "PyYAML>=5.3",
        "numpy>=1.24.0",
        "scipy>=1.0.0",
        "pymongo==3.11.3",
        "psutil==5.6.6",
        "pytest>6.2",
        "Flask>=2.0.1",
        "Werkzeug>=2.0.1",
        "statsmodels==0.14.0",
        "PyPDF2>=2.5.0",
        "pyarrow>=14.0.1",
        "scikit-learn>1.3.0",
    ],
    tests_require=["nose", "flake8"],
    extras_require=dict(),
    test_suite="nose.collector",
    include_package_data=True,
)
