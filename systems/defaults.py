"""
All default parameters that might be used in a system are stored here

Order of preferences is - passed in command line to calculation method,
                          stored in system config object
                          found in defaults

"""
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_data, arg_not_supplied
import yaml

DEFAULT_FILENAME = "systems.provided.defaults.yaml"


def get_system_defaults():
    """
    >>> system_defaults['average_absolute_forecast']
    10.0
    """
    default_file = get_filename_for_package(DEFAULT_FILENAME)
    with open(default_file) as file_to_parse:
        default_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)

    return default_dict


def get_default_config_key_value(key_name,
                                 system_defaults_dict=arg_not_supplied):
    if system_defaults_dict is arg_not_supplied:
        default_config_dict = get_system_defaults()
    else:
        default_config_dict = system_defaults_dict

    key_value = default_config_dict.get(key_name, missing_data)

    return key_value


system_defaults = get_system_defaults()

if __name__ == "__main__":
    import doctest

    doctest.testmod()
