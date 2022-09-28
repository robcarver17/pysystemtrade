import os
from sysdata.config.configdata import Config
from sysdata.config.private_config import PRIVATE_CONFIG_DIR_ENV_VAR, DEFAULT_PRIVATE_DIR
from yaml.parser import ParserError

PRIVATE_CONTROL_CONFIG_FILE = "private_control_config.yaml"
DEFAULT_CONTROL_CONFIG_FILE = "syscontrol.control_config.yaml"


def get_control_config() -> Config:

    if os.getenv(PRIVATE_CONFIG_DIR_ENV_VAR):
        private_control_path = f"{os.environ[PRIVATE_CONFIG_DIR_ENV_VAR]}/{PRIVATE_CONTROL_CONFIG_FILE}"
    else:
        private_control_path = f"{DEFAULT_PRIVATE_DIR}/{PRIVATE_CONTROL_CONFIG_FILE}"

    try:
        control_config = Config(
            private_filename=private_control_path,
            default_filename=DEFAULT_CONTROL_CONFIG_FILE
        )
        control_config.fill_with_defaults()

    except ParserError as pe:
        raise Exception("YAML syntax problem: %s" % str(pe))
    except FileNotFoundError:
        raise Exception(
            "Need to have either %s or %s or both present:"
            % (str(DEFAULT_CONTROL_CONFIG_FILE), str(private_control_path))
        )
    except BaseException as be:
        raise Exception("Problem reading control config: %s" % str(be))

    return control_config
