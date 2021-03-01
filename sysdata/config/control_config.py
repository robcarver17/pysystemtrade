from sysdata.config.configdata import Config

PRIVATE_CONTROL_CONFIG_FILE = "private.private_control_config.yaml"
DEFAULT_CONTROL_CONFIG_FILE = "syscontrol.control_config.yaml"

def get_control_config() -> Config:
    try:
        control_config = Config(PRIVATE_CONTROL_CONFIG_FILE, default_filename=DEFAULT_CONTROL_CONFIG_FILE)
        control_config.fill_with_defaults()
    except:
        raise Exception("Need to have either %s or %s or both present:" % (
        str(DEFAULT_CONTROL_CONFIG_FILE), str(PRIVATE_CONTROL_CONFIG_FILE)))

    return control_config
