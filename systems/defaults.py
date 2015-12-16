"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method, 
                          stored in system config object
                          found in defaults

"""
from syscore.fileutils import get_pathname_for_package
import systems
import yaml

def get_system_defaults():
    """
    >>> defaults=system_defaults()
    >>> defaults['average_absolute_forecast']
    10.0
    """
    default_file=get_pathname_for_package("systems", "provided", "defaults.yaml")
    with open(default_file) as file_to_parse:
        default_dict=yaml.load(file_to_parse)

    return default_dict

system_defaults=get_system_defaults()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
