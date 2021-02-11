
def fill_config_dict_with_defaults(config_dict, defaults_dict):
    """
    >>> fill_config_dict_with_defaults({a:2}, {b:3})
    """
    ## Substitute in default values from config_dict where missing from defaults_dict
    ## Works at multiple levels
    default_keys = list(defaults_dict.keys())
    config_keys = list(config_dict.keys())
    joint_keys = list(set(default_keys+config_keys))

    for key in joint_keys:
        config_value = config_dict.get(key, None)
        default_value = defaults_dict.get(key, None)
        if config_value is None:
            config_value = default_value
        elif default_value is None:
            continue
        elif type(config_value) is dict and type(defaults_dict) is dict:
            config_value = fill_config_dict_with_defaults(config_value, default_value)

        config_dict[key] = config_value

    return config_dict