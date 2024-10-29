import glob
import datetime
import time
from importlib import import_module
import os
from pathlib import Path
from typing import List, Tuple

from syscore.dateutils import SECONDS_PER_DAY

# DO NOT DELETE: all these are unused: but are required to get the filename padding to work


"""

    FILES IN DIRECTORIES

"""

"""

    FILE RENAMING AND DELETING

"""


def rename_files_with_extension_in_pathname_as_archive_files(
    pathname: str, extension: str = ".txt", archive_extension: str = ".arch"
):
    """
    Find all the files with a particular extension in a directory, and rename them
     eg thing.txt will become thing_yyyymmdd.txt where yyyymmdd is todays date

    """

    resolved_pathname = get_resolved_pathname(pathname)
    list_of_files = files_with_extension_in_resolved_pathname(
        resolved_pathname, extension=extension
    )

    for filename in list_of_files:
        full_filename = os.path.join(resolved_pathname, filename)
        rename_file_as_archive(
            full_filename, old_extension=extension, archive_extension=archive_extension
        )


def rename_file_as_archive(
    full_filename: str, old_extension: str = ".txt", archive_extension: str = ".arch"
):
    """
    Rename a file with archive suffix and extension
     eg thing.txt will become thing_yyyymmdd.arch where yyyymmdd is todays date

    """

    old_filename = "%s%s" % (full_filename, old_extension)
    date_label = datetime.datetime.now().strftime("%Y%m%d")
    new_filename = "%s_%s%s" % (full_filename, date_label, archive_extension)

    os.rename(old_filename, new_filename)


def delete_old_files_with_extension_in_pathname(
    pathname: str, days_old=30, extension=".arch"
):
    """
    Find all the files with a particular extension in a directory, and delete them
    if older than x days

    """

    resolved_pathname = get_resolved_pathname(pathname)
    list_of_files = glob.glob(resolved_pathname + "/**/*" + extension, recursive=True)

    for filename in list_of_files:
        delete_file_if_too_old(filename, days_old=days_old)


def delete_file_if_too_old(full_filename_with_ext: str, days_old: int = 30):
    file_age = get_file_or_folder_age_in_days(full_filename_with_ext)
    if file_age > days_old:
        print("Deleting %s" % full_filename_with_ext)
        os.remove(full_filename_with_ext)


def get_file_or_folder_age_in_days(full_filename_with_ext: str) -> float:
    # time will be in UNIX seconds
    file_time = os.stat(full_filename_with_ext).st_ctime
    time_now = time.time()

    age_seconds = time_now - file_time
    age_days = age_seconds / SECONDS_PER_DAY

    return age_days


"""

    FILENAME RESOLUTION

"""


def resolve_path_and_filename_for_package(
    path_and_filename: str, separate_filename=None
) -> str:
    """
    A way of resolving relative and absolute filenames, and dealing with awkward OS specific things

    >>> resolve_path_and_filename_for_package("/home/rob/", "file.csv")
    '/home/rob/file.csv'

    >>> resolve_path_and_filename_for_package(".home.rob", "file.csv")
    '/home/rob/file.csv'

    >>> resolve_path_and_filename_for_package('C:\\home\\rob\\'', "file.csv")
    'C:\\home\\rob\\file.csv'

    >>> resolve_path_and_filename_for_package("syscore.tests", "file.csv")
    '/home/rob/pysystemtrade/syscore/tests/file.csv'

    >>> resolve_path_and_filename_for_package("/home/rob/file.csv")
    '/home/rob/file.csv'

    >>> resolve_path_and_filename_for_package(".home.rob.file.csv")
    '/home/rob/file.csv'

    >>> resolve_path_and_filename_for_package("C:\\home\\rob\\file.csv")
    'C:\\home\\rob\\file.csv'

    >>> resolve_path_and_filename_for_package("syscore.tests.file.csv")
    '/home/rob/pysystemtrade/syscore/tests/file.csv'

    """

    path_and_filename_as_list = transform_path_into_list(path_and_filename)
    if separate_filename is None:
        (
            path_as_list,
            separate_filename,
        ) = extract_filename_from_combined_path_and_filename_list(
            path_and_filename_as_list
        )
    else:
        path_as_list = path_and_filename_as_list

    resolved_pathname = get_pathname_from_list(path_as_list)

    resolved_path_and_filename = os.path.join(resolved_pathname, separate_filename)

    return resolved_path_and_filename


def get_resolved_pathname(pathname: str) -> str:
    """
    >>> get_resolved_pathname("/home/rob/")
    '/home/rob'

    >>> get_resolved_pathname(".home.rob")
    '/home/rob'

    >>> get_resolved_pathname('C:\\home\\rob\\'')
    'C:\\home\\rob'

    >>> get_resolved_pathname("syscore.tests")
    '/home/rob/pysystemtrade/syscore/tests'

    """

    if isinstance(pathname, Path):
        # special case when already a Path
        pathname = str(pathname.absolute())

    if "@" in pathname:
        # This is an ssh address for rsync - don't change
        return pathname

    # Turn /,\ into . so system independent
    path_as_list = transform_path_into_list(pathname)
    resolved_pathname = get_pathname_from_list(path_as_list)

    return resolved_pathname


## something unlikely to occur naturally in a pathname
RESERVED_CHARACTERS = "&!*"


def transform_path_into_list(pathname: str) -> List[str]:
    """
    >>> path_as_list("/home/rob/test.csv")
    ['', 'home', 'rob', 'test', 'csv']

    >>> path_as_list("/home/rob/")
    ['', 'home', 'rob']

    >>> path_as_list(".home.rob")
    ['', 'home', 'rob']

    >>> path_as_list('C:\\home\\rob\\'')
    ['C:', 'home', 'rob']

    >>> path_as_list('C:\\home\\rob\\test.csv')
    ['C:', 'home', 'rob', 'test', 'csv']

    >>> path_as_list("syscore.tests.fileutils.csv")
    ['syscore', 'tests', 'fileutils', 'csv']

    >>> path_as_list("syscore.tests")
    ['syscore', 'tests']

    """

    pathname_replace = add_reserved_characters_to_pathname(pathname)
    path_as_list = pathname_replace.rsplit(RESERVED_CHARACTERS)

    if path_as_list[-1] == "":
        path_as_list.pop()

    return path_as_list


def add_reserved_characters_to_pathname(pathname: str) -> str:
    pathname_replace = pathname.replace(".", RESERVED_CHARACTERS)
    pathname_replace = pathname_replace.replace("/", RESERVED_CHARACTERS)
    pathname_replace = pathname_replace.replace("\\", RESERVED_CHARACTERS)

    return pathname_replace


def extract_filename_from_combined_path_and_filename_list(
    path_and_filename_as_list: list,
) -> Tuple[list, str]:
    """
    >>> extract_filename_from_combined_path_and_filename_list(['home', 'rob','file', 'csv'])
    (['home', 'rob'], 'file.csv')
    """
    ## need -2 because want extension
    extension = path_and_filename_as_list.pop()
    filename = path_and_filename_as_list.pop()

    separate_filename = ".".join([filename, extension])

    return path_and_filename_as_list, separate_filename


def get_pathname_from_list(path_as_list: List[str]) -> str:
    """
    >>> get_pathname_from_list(['C:', 'home', 'rob'])
    'C:\\home\\rob'
    >>> get_pathname_from_list(['','home','rob'])
    '/home/rob'
    >>> get_pathname_from_list(['syscore','tests'])
    '/home/rob/pysystemtrade/syscore/tests'
    """
    if path_as_list[0] == "":
        # path_type_absolute
        resolved_pathname = get_absolute_linux_pathname_from_list(path_as_list[1:])
    elif is_windoze_path_list(path_as_list):
        # windoze
        resolved_pathname = get_absolute_windows_pathname_from_list(path_as_list)
    else:
        # relative
        resolved_pathname = get_relative_pathname_from_list(path_as_list)

    return resolved_pathname


def is_windoze_path_list(path_as_list: List[str]) -> bool:
    """
    >>> is_windoze_path_list(['C:'])
    True
    >>> is_windoze_path_list(['wibble'])
    False
    """
    return path_as_list[0].endswith(":")


def get_relative_pathname_from_list(path_as_list: List[str]) -> str:
    """

    >>> get_relative_pathname_from_list(['syscore','tests'])
    '/home/rob/pysystemtrade/syscore/tests'
    """
    package_name = path_as_list[0]
    paths_or_files = path_as_list[1:]

    if len(paths_or_files) == 0:
        directory_name_of_package = os.path.dirname(
            import_module(package_name).__file__
        )
        return directory_name_of_package

    last_item_in_list = path_as_list.pop()
    pathname = os.path.join(
        get_relative_pathname_from_list(path_as_list), last_item_in_list
    )

    return pathname


def get_absolute_linux_pathname_from_list(path_as_list: List[str]) -> str:
    """
    Returns the absolute pathname from a list

    >>> get_absolute_linux_pathname_from_list(['home', 'rob'])
    '/home/rob'
    """
    pathname = os.path.join(*path_as_list)
    pathname = os.path.sep + pathname

    return pathname


def get_absolute_windows_pathname_from_list(path_as_list: list) -> str:
    """
    Test will fail on linux
    >>> get_absolute_windows_pathname_from_list(['C:','home','rob'])
    'C:\\home\\rob'
    """
    drive_part_of_path = path_as_list[0]
    if drive_part_of_path.endswith(":"):
        ## add back backslash
        drive_part_of_path = drive_part_of_path.replace(":", ":\\")
        path_as_list[0] = drive_part_of_path

    pathname = os.path.join(*path_as_list)

    return pathname


"""

    HTML

"""


def write_list_of_lists_as_html_table_in_file(file, list_of_lists: list):
    file.write("<table>")
    for sublist in list_of_lists:
        file.write("  <tr><td>")
        file.write("    </td><td>".join(sublist))
        file.write("  </td></tr>")

    file.write("</table>")


def files_with_extension_in_pathname(pathname: str, extension=".csv") -> List[str]:
    """
    Find all the files with a particular extension in a directory

    """
    resolved_pathname = get_resolved_pathname(pathname)

    return files_with_extension_in_resolved_pathname(
        resolved_pathname, extension=extension
    )


def files_with_extension_in_resolved_pathname(
    resolved_pathname: str, extension=".csv"
) -> List[str]:
    """
    Find all the files with a particular extension in a directory
    """

    file_list = os.listdir(resolved_pathname)
    file_list = [filename for filename in file_list if filename.endswith(extension)]
    file_list_no_extension = [filename.split(".")[0] for filename in file_list]

    return file_list_no_extension


def full_filename_for_file_in_home_dir(filename: str) -> str:
    pathname = os.path.expanduser("~")

    return os.path.join(pathname, filename)


def does_filename_exist(filename: str) -> bool:
    resolved_filename = resolve_path_and_filename_for_package(filename)
    file_exists = does_resolved_filename_exist(resolved_filename)
    return file_exists


def does_resolved_filename_exist(resolved_filename: str) -> bool:
    file_exists = os.path.isfile(resolved_filename)
    return file_exists
