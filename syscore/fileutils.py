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
import sysbrokers
import sysproduction

def get_filename_for_package(pathname, filename=None):
    """
    A way of resolving relative and absolute filenames, and dealing with akward OS specific things

    We can eithier have pathname = 'some.path.filename.csv' or pathname='some.path', filename='filename.csv'

    An absolute filename is a full path

    A relative filename sits purely within the pysystemtrade directory, eg sysbrokers.IB.config.csv resolves to
       ..../pysystemtrade/sysbrokers/IB/config.csv

    We can pass eithier:

    - a relative filename demarcated with .
    - an absolute filename demarcated with ., / or \

    Absolute filenames always begin with ., / or \
    Relative filenames do not
    """
    dotted_pathname = add_dots_to_pathname(pathname)
    if filename is None:
        # filename will be at the end of the pathname
        path_as_list = dotted_pathname.rsplit(".")
        filename = '.'.join(path_as_list[-2:])
        split_pathname = '.'.join(path_as_list[0:-2])
    else:
        # filename is already seperate
        split_pathname = dotted_pathname

    ## Resolve pathname
    resolved_pathname = get_resolved_dotted_pathname(split_pathname)

    # Glue together
    full_path_and_file = os.path.join(resolved_pathname, filename)

    return full_path_and_file

def add_dots_to_pathname(pathname):
    pathname_replaced = pathname.replace("/", ".")
    pathname_replaced = pathname_replaced.replace("\\", ".")

    return pathname_replaced

def get_resolved_pathname(pathname):
    ## Turn /,\ into . so system independent
    pathname_replaced = add_dots_to_pathname(pathname)
    resolved_pathname = get_resolved_dotted_pathname(pathname_replaced)

    return resolved_pathname

def get_resolved_dotted_pathname(pathname):
    path_as_list = pathname.rsplit(".")

    ## Check for absolute or relative
    pathname = get_pathname_from_list(path_as_list)

    return pathname


def get_pathname_from_list(path_as_list):
    if path_as_list[0] == "":
        #path_type_absolute
        resolved_pathname = get_absolute_pathname_from_list(path_as_list[1:])
    else:
        # relativee
        resolved_pathname = get_pathname_for_package_from_list(path_as_list)

    return resolved_pathname



def get_pathname_for_package_from_list(path_as_list):
    """
    Returns the filename of part of a package from a list

    :param path_as_list: List of path  ["syscore","subdirector"] in pysystemtrade world
    :type path_as_list: list of str

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


def get_absolute_pathname_from_list(path_as_list):
    """
    Returns the absolute pathname from a list

    :param path_as_list: List of path and file name eg ["syscore","fileutils.py"]
    :type path_as_list:

    :returns: full pathname of package
    """
    pathname = os.path.join(*path_as_list)
    pathname = os.path.sep + pathname

    return pathname


def files_with_extension_in_pathname(pathname, extension=".csv"):
    """
    Find all the files with a particular extension in a directory

    :param pathname: absolute eg "home/user/data" or relative inside pysystemtrade eg "data.futures"
    :param extension: str
    :return: list of files, with extensions stripped off
    """
    pathname = get_resolved_pathname(pathname)

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
