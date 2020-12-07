from syscore.genutils import get_safe_from_dict
from sysdata.private_config import get_list_of_private_then_default_key_values

DEFAULT_IB_IPADDRESS = "127.0.0.1"
DEFAULT_IB_PORT = 4001
DEFAULT_IB_IDOFFSET = 1
LIST_OF_IB_PARAMS = ["ipaddress", "port", "idoffset"]


def ib_defaults(**kwargs):
    """
    Returns ib configuration with following precedence
    1- if passed in arguments: ipaddress, port, idoffset - use that
    2- if defined in private_config file, use that. ib_ipaddress, ib_port, ib_idoffset
    3 - if defined in system defaults file, use that
    4- otherwise use defaults DEFAULT_IB_IPADDRESS, DEFAULT_IB_PORT, DEFAULT_IB_IDOFFSET

    :return: mongo db, hostname, port
    """

    param_names_with_prefix = [
        "ib_" + arg_name for arg_name in LIST_OF_IB_PARAMS]
    config_dict = get_list_of_private_then_default_key_values(
        param_names_with_prefix)

    yaml_dict = {}
    for arg_name in LIST_OF_IB_PARAMS:
        yaml_arg_name = "ib_" + arg_name

        # Start with config (precedence: private config, then system config)
        arg_value = config_dict[yaml_arg_name]
        # Overwrite with kwargs
        arg_value = get_safe_from_dict(kwargs, arg_name, arg_value)

        # Write
        yaml_dict[arg_name] = arg_value

    # Get from dictionary
    ipaddress = yaml_dict.get("ipaddress", DEFAULT_IB_IPADDRESS)
    port = yaml_dict.get("port", DEFAULT_IB_PORT)
    idoffset = yaml_dict.get("idoffset", DEFAULT_IB_IDOFFSET)

    return ipaddress, port, idoffset