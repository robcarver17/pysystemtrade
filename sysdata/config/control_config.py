from sysdata.config.configdata import Config

PRIVATE_CONTROL_CONFIG_FILE = "private.private_control_config.yaml"
DEFAULT_CONTROL_CONFIG_FILE = "syscontrol.control_config.yaml"

def get_control_config():
    control_config = Config(PRIVATE_CONTROL_CONFIG_FILE, default_filename=DEFAULT_CONTROL_CONFIG_FILE)
    control_config.fill_with_defaults()

    return control_config

control_config = get_control_config()
