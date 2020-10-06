import re
from copy import copy


def sort_dict_by_underscore_length(other_args):
    """
    Sort dict according to keys and presence of leading underscores

    :param other_args: dict
    :return: list of dict. First element is dict of all keys with no leading underscores.
             Second element is dict of all keys with 1 leading underscore...and so on
    """
    other_arg_keys = list(other_args.keys())
    other_arg_keys_sorted = sort_keywords_by_underscore_length(other_arg_keys)

    sorted_list_of_dicts = []
    for list_of_args in other_arg_keys_sorted:
        extracted_dict = dict([(key, other_args[key]) for key in list_of_args])
        sorted_list_of_dicts.append(extracted_dict)

    return sorted_list_of_dicts


def sort_keywords_by_underscore_length(other_arg_keys):
    """
    Sort other_arg_keys depending on their leading underscores

    Does not strip the underscores!

    :param other_arg_keys: list of str
    :return: list of list of str. First element is list of all keys with no leading underscores.
             Second element is list of all keys with 1 leading underscore...and so on
    """

    counted_keys = dict(
        [
            (key_value, count_leading_underscores_in_string(key_value))
            for key_value in other_arg_keys
        ]
    )
    count_values = list(counted_keys.values())
    max_key = max(count_values)

    sorted_keywords = []
    for key_len in range(max_key + 1):
        keys_with_key_value = [
            key for key,
            key_value in counted_keys.items() if key_value == key_len]
        sorted_keywords.append(keys_with_key_value)

    return sorted_keywords


def count_leading_underscores_in_string(process_string):
    """
    How many underscores at start of process string

    :param process_string: str
    :return: int
    """
    if len(process_string) == 0:
        raise Exception(
            "Can't pass a parameter name consisting only of underscores or a zero length string"
        )

    if process_string[0] == "_":
        return count_leading_underscores_in_string(process_string[1:]) + 1

    return 0


def strip_underscores_from_dict_keys(arg_dict):
    """

    :param arg_dict: dict, with key names that may have leading underscores in them of any length
    :return: dict with underscores removed from keynames
    """

    new_dict = dict(
        [
            (strip_leading_underscores_from_str(old_key), dict_value)
            for old_key, dict_value in arg_dict.items()
        ]
    )

    return new_dict


def strip_leading_underscores_from_str(process_string):
    return re.sub("^[^A-Za-z]*", "", process_string)


def force_args_to_same_length(data_args_input, data, pad_with={}):
    """
    Ensure data_args is same length as data list, padding out

    :param data_args_input: list of objects
    :param data: list of objects
    :return: padded list
    """

    padded_data_args = []
    data_args = copy(data_args_input)
    while len(padded_data_args) < len(data):
        if len(data_args) == 0:
            # We have exhausted all the available data, need to pad with empty
            # dicts
            padded_data_args.append(pad_with)
        else:
            # We have more left
            padded_data_args.append(data_args.pop(0))
        # If we are done then the data and the padded arguments will now be the same length
        # The while condition will fail

    if len(data_args) > 0:
        print(
            "WARNING: some unused data arguments passed when creating trading rule (had %d leftover, only needed %d)" %
            (len(data_args), len(data)))

    return padded_data_args
