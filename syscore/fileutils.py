import glob
import datetime
import time
import os
import sys

from syscore.dateutils import SECONDS_PER_DAY

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

    We can either have pathname = 'some.path.filename.csv' or pathname='some.path', filename='filename.csv'

    An absolute filename is a full path

    A relative filename sits purely within the pysystemtrade directory, eg sysbrokers.IB.config.csv resolves to
       ..../pysystemtrade/sysbrokers/IB/config.csv

    We can pass either:

    - a relative filename demarcated with .
    - an absolute filename demarcated with ., / or \

    Absolute filenames always begin with ., / or \
    Relative filenames do not
    """
    dotted_pathname = add_dots_to_pathname(pathname)
    if filename is None:
        # filename will be at the end of the pathname
        path_as_list = dotted_pathname.rsplit(".")
        filename = ".".join(path_as_list[-2:])
        split_pathname = ".".join(path_as_list[0:-2])
    else:
        # filename is already separate
        split_pathname = dotted_pathname

    # Resolve pathname
    resolved_pathname = get_resolved_dotted_pathname(split_pathname)

    # Glue together
    full_path_and_file = os.path.join(resolved_pathname, filename)

    return full_path_and_file


def add_dots_to_pathname(pathname):
    pathname_replaced = pathname.replace("/", ".")
    pathname_replaced = pathname_replaced.replace("\\", ".")

    return pathname_replaced


def get_resolved_pathname(pathname):
    # Turn /,\ into . so system independent
    pathname_replaced = add_dots_to_pathname(pathname)
    resolved_pathname = get_resolved_dotted_pathname(pathname_replaced)

    return resolved_pathname


def get_resolved_dotted_pathname(pathname):
    path_as_list = pathname.rsplit(".")

    # Check for absolute or relative
    pathname = get_pathname_from_list(path_as_list)

    return pathname


def get_pathname_from_list(path_as_list):
    if path_as_list[0] == "" or path_as_list[0].endswith(":"):
        # path_type_absolute
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
        get_pathname_for_package_from_list(path_as_list), last_item_in_list
    )

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
    file_list = [
        filename for filename in file_list if filename.endswith(extension)]
    file_list_no_extension = [filename.split(".")[0] for filename in file_list]

    return file_list_no_extension


def file_in_home_dir(filename):
    pathname = os.path.expanduser("~")

    return os.path.join(pathname, filename)


def rename_files_with_extension_in_pathname_as_archive(
    pathname, extension=".txt", new_extension=".arch"
):
    """
    Find all the files with a particular extension in a directory, and rename them
     eg thing.txt will become thing_yyyymmdd.txt where yyyymmdd is todays date

    :param pathname: absolute eg "home/user/data" or relative inside pysystemtrade eg "data.futures"
    :param extension: str
    :return: list of files, with extensions stripped off
    """

    list_of_files = files_with_extension_in_pathname(pathname, extension)
    pathname = get_resolved_pathname(pathname)

    for filename in list_of_files:
        full_filename = os.path.join(pathname, filename)
        rename_file_as_archive(
            full_filename, old_extension=extension, new_extension=new_extension
        )


def rename_file_as_archive(
        full_filename,
        old_extension=".txt",
        new_extension=".arch"):
    """
    Rename a file with archive suffix
     eg thing.txt will become thing_yyyymmdd.arch where yyyymmdd is todays date

    :param pathname: absolute eg "home/user/data" or relative inside pysystemtrade eg "data.futures"
    :param extension: str
    :return: list of files, with extensions stripped off
    """

    old_filename = "%s%s" % (full_filename, old_extension)
    date_label = datetime.datetime.now().strftime("%Y%m%d")
    new_filename = "%s_%s%s" % (full_filename, date_label, new_extension)

    os.rename(old_filename, new_filename)


def delete_old_files_with_extension_in_pathname(
    pathname, days_old=30, extension=".arch"
):
    """
    Find all the files with a particular extension in a directory, and delete them
    if older than x days

    :param pathname: absolute eg "home/user/data" or relative inside pysystemtrade eg "data.futures"
    :param extension: str
    :return: list of files, with extensions stripped off
    """

    pathname = get_resolved_pathname(pathname)
    list_of_files = glob.glob(pathname + "/**/*" + extension, recursive=True)

    for filename in list_of_files:
        delete_file_if_too_old(filename, days_old=days_old)


def delete_file_if_too_old(full_filename_with_ext, days_old=30):
    file_age = get_file_or_folder_age_in_days(full_filename_with_ext)
    if file_age > days_old:
        print("Deleting %s" % full_filename_with_ext)
        os.remove(full_filename_with_ext)


def get_file_or_folder_age_in_days(full_filename_with_ext):
    # time will be in seconds
    file_time = os.stat(full_filename_with_ext).st_ctime
    time_now = time.time()

    age_seconds = time_now - file_time
    age_days = age_seconds / SECONDS_PER_DAY
    return age_days


if __name__ == "__main__":
    import doctest

    doctest.testmod()
