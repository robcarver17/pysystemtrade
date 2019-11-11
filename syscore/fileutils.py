import os
import sys
import matplotlib.pylab as plt
from PIL import Image
from functools import partial

# all these are unused: but are required to get the filename padding to work
import syscore
import sysdata
import systems
import sysinit
import examples
import private
import data

def get_filename_for_package(pathname, filename=None):
    """
    Get a full filename given path and filename OR relative path+filename

    :param pathname: Absolute eg "/home/rob/pysystemtrader/data/thing" or relative eg "data.thing"
    :param filename: filename, or None if using
    :return: full resolved path and filename
    """
    if filename is None:
        # filename will be at the end of the pathname
        path_as_list = pathname.rsplit(".")
        filename = '.'.join(path_as_list[-2:])
        pathname = '.'.join(path_as_list[0:-2])

    resolved_pathname = get_pathname_for_package(pathname)

    return resolved_pathname+"/"+filename


def get_pathname_for_package(pathname):
    """
    Returns the resolved pathname given a relative pathname eg "sysdata.tests"

    If an absolute pathname, eg "home/user/pysystemtrade/sysdata/tests" is passed, just return it

    :param name_with_dots: Relative path name written with "." eg "sysdata.tests"
    :type str:

    :returns: full pathname of package eg "../sysdata/tests/"


    """
    if "/" in pathname:
        # don't need to sub in actual pathname
        return pathname

    path_as_list = pathname.rsplit(".")

    return get_pathname_for_package_from_list(path_as_list)


def get_pathname_for_package_from_list(path_as_list):
    """
    Returns the filename of part of a package from a list

    :param path_as_list: List of path and file name eg ["syscore","fileutils.py"]
    :type path_as_list:

    :returns: full pathname of package
    """
    package_name = path_as_list[0]
    paths_or_files = path_as_list[1:]
    d = os.path.dirname(sys.modules[package_name].__file__)

    if len(paths_or_files) == 0:
        return d

    last_item_in_list = path_as_list.pop()
    pathname = os.path.join(
        get_pathname_for_package_from_list(path_as_list), last_item_in_list)

    return pathname


def files_with_extension_in_pathname(pathname, extension=".csv"):
    """
    Find all the files with a particular extension in a directory

    :param pathname: absolute eg "home/user/data" or relative inside pysystemtrade eg "data.futures"
    :param extension: str
    :return: list of files, with extensions stripped off
    """
    pathname = get_pathname_for_package(pathname)

    file_list = os.listdir(pathname)
    file_list = [filename for filename in file_list if filename.endswith(extension)]
    file_list_no_extension = [filename.split('.')[0] for filename in file_list]

    return file_list_no_extension

def file_in_home_dir(filename):
    pathname = os.path.expanduser("~")

    return os.path.join(pathname, filename)

def image_process(filename):
    """
    Dumps the current plot to a low res and high res grayscale .jpg in the current users home directory
    Used by Rob for writing yet another of his dull books on trading

    :param filename: filename to write
    :return: None
    """

    fig = plt.gcf()
    fig.set_size_inches(18.5, 10.5)
    fig.savefig(file_in_home_dir("%s.png" % filename), dpi=300)
    fig.savefig(file_in_home_dir("%sLOWRES.png" % filename), dpi=50)

    Image.open(file_in_home_dir("%s.png" % filename)).convert('L').save(file_in_home_dir("%s.jpg" % filename))
    Image.open(file_in_home_dir("%sLOWRES.png" % filename)).convert('L').save(file_in_home_dir("%sLOWRES.jpg" % filename))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
