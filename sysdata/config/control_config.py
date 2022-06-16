from sysdata.config.configdata import Config
from yaml.parser import ParserError

PRIVATE_CONTROL_CONFIG_FILE = "private.private_control_config.yaml"
DEFAULT_CONTROL_CONFIG_FILE = "syscontrol.control_config.yaml"


def get_control_config() -> Config:
    try:
        control_config = Config(
            PRIVATE_CONTROL_CONFIG_FILE, default_filename=DEFAULT_CONTROL_CONFIG_FILE
        )

    except ParserError as pe:
        raise Exception("YAML syntax problem: %s" % str(pe))
    except FileNotFoundError:
        raise Exception(
            "Need to have either %s or %s or both present:"
            % (str(DEFAULT_CONTROL_CONFIG_FILE), str(PRIVATE_CONTROL_CONFIG_FILE))
        )
    except BaseException as be:
        raise Exception("Problem reading control config: %s" % str(be))

    return control_config
