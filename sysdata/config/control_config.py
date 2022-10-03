from sysdata.config.configdata import Config
from sysdata.config.private_directory import get_full_path_for_config
from yaml.parser import ParserError

PRIVATE_CONTROL_CONFIG_FILE = "private_control_config.yaml"
DEFAULT_CONTROL_CONFIG_FILE = "syscontrol.control_config.yaml"


def get_control_config() -> Config:

    private_control_path = get_full_path_for_config(PRIVATE_CONTROL_CONFIG_FILE)

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
