from syscore.fileutils import does_file_exist
from syscore.fileutils import get_filename_for_package
from syscore.objects import arg_not_supplied
from sysdata.config.private_directory import get_full_path_for_config

import yaml

PRIVATE_CONFIG_FILE = "private_config.yaml"


def get_private_config_as_dict(filename:str = arg_not_supplied) -> dict:
    if filename is arg_not_supplied:
        filename = get_full_path_for_config(PRIVATE_CONFIG_FILE)
    if not does_file_exist(filename):
        print(
            "Private configuration %s does not exist; no problem if running in sim mode"
            % filename
        )

        return {}

    private_file = get_filename_for_package(filename)
    with open(private_file) as file_to_parse:
        private_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)

    return private_dict
