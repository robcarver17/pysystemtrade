"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method,
                          stored in system config object
                          found in defaults

"""
from syscore.fileutils import get_filename_for_package
import yaml

DEFAULT_FILENAME = "systems.provided.defaults.yaml"


def get_system_defaults():
    """
    >>> system_defaults['average_absolute_forecast']
    10.0
    """
    default_file = get_filename_for_package(DEFAULT_FILENAME)
    with open(default_file) as file_to_parse:
        default_dict = yaml.load(file_to_parse)

    return default_dict


system_defaults = get_system_defaults()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
