import os
import sys

def get_pathname_for_package(package_name, path=""):
    """
    Returns the filename of part of a package
    
    eg get_pathname_for_package("syscore", "fileutils.py") will return the location of this files
    """

    d = os.path.dirname(sys.modules[package_name].__file__)
    pathname = os.path.join(d,  path)

    return pathname