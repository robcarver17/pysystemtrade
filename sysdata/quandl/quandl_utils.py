from sysdata.private_config import get_private_config_key_value
from syscore.objects import missing_data


def load_private_key():
    """
    Tries to load a private key

    :return: key
    """
    dict_key = "quandl_key"

    key = get_private_config_key_value(dict_key)
    if key is missing_data:
        # no private key
        print("No private key found for QUANDL - you will be subject to data limits")
        key = None

    return key
