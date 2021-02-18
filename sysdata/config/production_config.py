from sysdata.config.configdata import Config

PRIVATE_CONFIG_FILE = "private.private_config.yaml"


def get_production_config() -> Config:
    config = Config(PRIVATE_CONFIG_FILE)
    config.fill_with_defaults()

    return config

production_config = get_production_config()


