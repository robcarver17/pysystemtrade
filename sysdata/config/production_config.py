from sysdata.config.configdata import Config
from syscore.fileutils import does_file_exist

PRIVATE_CONFIG_FILE = "private.private_config.yaml"


def get_production_config() -> Config:
    if private_config_file_exists():
        config = Config(PRIVATE_CONFIG_FILE)
    else:
        print("Private configuration %s does not exist; no problem if running in sim mode" % PRIVATE_CONFIG_FILE)
        config = Config({})

    config.fill_with_defaults()

    return config

def private_config_file_exists()-> bool:
    return does_file_exist(PRIVATE_CONFIG_FILE)
