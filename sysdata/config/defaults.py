"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method,
                          stored in system config object
                          found in defaults

"""
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied, missing_data
import yaml

DEFAULT_FILENAME = "sysdata.config.defaults.yaml"


def get_system_defaults_dict(filename: str = arg_not_supplied) -> dict:
    """
    >>> system_defaults['average_absolute_forecast']
    10.0
    """
    if filename is arg_not_supplied:
        filename = DEFAULT_FILENAME
    default_file = get_filename_for_package(filename)
    with open(default_file) as file_to_parse:
        default_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)

    return default_dict


system_defaults = get_system_defaults_dict()

if __name__ == "__main__":
    import doctest

    doctest.testmod()
