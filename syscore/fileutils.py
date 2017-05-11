import os
import sys
import syscore
import sysdata
import systems
import examples
import private


def get_filename_for_package(name_with_dots):
    """
    Returns the filename of part of a package

    :param name_with_dots: Path and file name written with "." eg "syscore.fileutils.py"
    :type str:

    :returns: full pathname of package
    >>>

    """
    path_as_list = name_with_dots.rsplit(".")

    # join last two things together. This is probably the most obfuscated code
    # I've ever written
    if len(path_as_list) >= 2:
        path_as_list[-1] = path_as_list[-2] + "." + path_as_list.pop()

    return get_pathname_for_package_from_list(path_as_list)


def get_pathname_for_package(name_with_dots):
    """
    Returns the pathname of part of a package

    :param name_with_dots: Path and file name written with "." eg "sysdata.tests"
    :type str:

    :returns: full pathname of package eg "../sysdata/tests/"


    """
    path_as_list = name_with_dots.rsplit(".")

    return get_pathname_for_package_from_list(path_as_list)


def get_pathname_for_package_from_list(path_as_list):
    """
    Returns the filename of part of a package

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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
