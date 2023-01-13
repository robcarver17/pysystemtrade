from sysdata.config.configdata import Config


def get_list_of_bad_instruments_in_config(config: Config) -> list:
    exclude_config = get_config_of_excluded_instruments(config)
    bad_markets = exclude_config.get("bad_markets", [])

    return bad_markets


def get_list_of_untradeable_instruments_in_config(config: Config) -> list:
    exclude_config = get_config_of_excluded_instruments(config)
    trading_restrictions = exclude_config.get("trading_restrictions", [])

    return trading_restrictions


def get_list_of_ignored_instruments_in_config(config: Config) -> list:
    exclude_config = get_config_of_excluded_instruments(config)
    ignore_instruments = exclude_config.get("ignore_instruments", [])

    return ignore_instruments


def get_config_of_excluded_instruments(config: Config) -> dict:
    exclude_instrument_lists = config.get_element_or_default(
        "exclude_instrument_lists", {}
    )
    return exclude_instrument_lists


def generate_matching_duplicate_dict(config: Config):
    """
    Returns a dict, each element is a named set of duplicated instruments
    Within each dict we have two elements: included, excluded
    Each of these is a list

    For example:
    dict(copper = dict(included = ["COPPER"], excluded = ["COPPER_mini"]
    """

    duplicate_instruments_config = config.get_element("duplicate_instruments")
    exclude_dict = duplicate_instruments_config.get("exclude", {})
    include_dict = duplicate_instruments_config.get("include", {})

    joint_keys = list(set(list(exclude_dict.keys()) + list(include_dict.keys())))

    results_dict = dict(
        [
            (key, get_duplicate_dict_entry(key, include_dict, exclude_dict))
            for key in joint_keys
        ]
    )

    return results_dict


def get_duplicate_dict_entry(key: str, include_dict: dict, exclude_dict: dict) -> dict:

    include_entry = get_entry_for_key_in_dict(key, include_dict, is_include_dict=True)
    exclude_entry = get_entry_for_key_in_dict(key, exclude_dict, is_include_dict=False)

    return dict(included=include_entry, excluded=exclude_entry)


def get_entry_for_key_in_dict(key: str, check_dict: dict, is_include_dict: bool = True):

    if key not in check_dict.keys():
        if is_include_dict:
            print(
                "%s is under duplicate_instruments['exclude_dict'] but not include_dict: should match"
                % key
            )
        else:
            print(
                "%s is under duplicate_instruments['include_dict'] but not exclude_dict: should match"
                % key
            )
        entry = []
    else:
        entry = check_dict[key]

    if not type(entry) is list:
        entry = [entry]

    return entry


def get_duplicate_list_of_instruments_to_remove_from_config(config: Config) -> list:
    duplicate_instruments_config = config.get_element_or_default(
        "duplicate_instruments", {}
    )

    exclude_dict = duplicate_instruments_config.get("exclude", {})
    list_of_duplicates = list(exclude_dict.values())

    ## do this because can have multiple duplicates
    duplicate_list_flattened = []
    for item in list_of_duplicates:
        if type(item) is list:
            duplicate_list_flattened = duplicate_list_flattened + item
        else:
            duplicate_list_flattened.append(item)

    return duplicate_list_flattened
