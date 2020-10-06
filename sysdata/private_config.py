import yaml
from syscore.fileutils import get_filename_for_package
from syscore.objects import missing_data, arg_not_supplied
from systems.defaults import (
    get_default_config_key_value,
    get_system_defaults,
    DEFAULT_FILENAME,
)

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")


def get_private_config():
    try:
        with open(PRIVATE_CONFIG_FILE) as file_to_parse:
            config_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)
    except BaseException:
        config_dict = {}

    return config_dict


def get_private_config_key_value(
    key_name, private_config_dict=arg_not_supplied, raise_error=False
):
    if private_config_dict is arg_not_supplied:
        private_config_dict = get_private_config()
    key_value = private_config_dict.get(key_name, missing_data)

    if key_value is missing_data and raise_error:
        raise KeyError(
            "Can't find key '%s' in private config file '%s'"
            % (key_name, PRIVATE_CONFIG_FILE)
        )

    return key_value


def get_private_then_default_key_value(
    key_name,
    system_defaults_dict=arg_not_supplied,
    private_config_dict=arg_not_supplied,
    raise_error=True,
):

    key_value = get_private_config_key_value(
        key_name, private_config_dict=private_config_dict
    )
    if key_value is missing_data:
        key_value = get_default_config_key_value(
            key_name, system_defaults_dict=system_defaults_dict
        )

    if key_value is missing_data and raise_error:
        raise KeyError(
            "Can't find key '%s' in private '%s' or default '%s' config .yaml files" %
            (key_name, PRIVATE_CONFIG_FILE, DEFAULT_FILENAME))

    return key_value


def get_list_of_private_then_default_key_values(
    list_of_key_names, fail_if_any_missing=True
):
    result_dict = {}
    system_defaults_dict = get_system_defaults()
    private_config_dict = get_private_config()

    for key_name in list_of_key_names:
        key_value = get_private_then_default_key_value(
            key_name,
            system_defaults_dict=system_defaults_dict,
            private_config_dict=private_config_dict,
            raise_error=fail_if_any_missing,
        )
        result_dict[key_name] = key_value

    return result_dict


def get_list_of_private_config_values(
        list_of_key_names,
        fail_if_any_missing=True):
    result_dict = {}
    private_config_dict = get_private_config()

    for key_name in list_of_key_names:
        key_value = get_private_config_key_value(
            key_name,
            private_config_dict=private_config_dict,
            raise_error=fail_if_any_missing,
        )
        result_dict[key_name] = key_value

    return result_dict
