import yaml
from sysdata.config.configdata import Config
from syscore.fileutils import get_filename_for_package

PRIVATE_CONFIG_FILE = get_filename_for_package("private.private_config.yaml")

def get_private_config() -> Config:
    config_as_dict = get_private_config_as_dict()
    config = Config(config_as_dict)
    config.fill_with_defaults()

    return config

def get_private_config_as_dict() -> dict:
    try:
        with open(PRIVATE_CONFIG_FILE) as file_to_parse:
            config_dict = yaml.load(file_to_parse, Loader=yaml.FullLoader)
    except BaseException:
        config_dict = {}

    return config_dict


