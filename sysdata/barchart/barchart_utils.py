import yaml

from syscore.fileutils import get_filename_for_package

BARCHART_PRIVATE_KEY_FILE = get_filename_for_package("private.private_config.yaml")

def load_private_key(key_file =BARCHART_PRIVATE_KEY_FILE , dict_key = 'barchart_key'):
    """
    Tries to load a private key

    :return: key
    """

    try:
        with open(key_file) as file_to_parse:
            yaml_dict = yaml.load(file_to_parse)
        key = yaml_dict[dict_key]
    except:
        # no private key
        print("No private key found for BARCHART - you will be subject to data limits")
        key = None

    return key
