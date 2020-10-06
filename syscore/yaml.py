import yaml


def pretty_write_nested_dict_to_yaml(nested_dict, file_handle):
    """
    Writes a nested dict to a yaml file

    :param nested_dict: A nested dict
    :param file_handle:
    :return: None
    """

    keynames = sorted(nested_dict.keys())

    for key in keynames:
        inner_dict = nested_dict[key]
        file_handle.write(yaml.dump(inner_dict, default_flow_style=False))
