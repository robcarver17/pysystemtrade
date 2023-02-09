import re
from copy import copy
from typing import List

from syscore.constants import arg_not_supplied


def sort_dict_by_underscore_length(some_dict: dict) -> List[dict]:
    """
    Sort dict according to keys and presence of leading underscores

    :return: list of dict. First element is dict of all keys with no leading underscores.
             Second element is dict of all; keys with 1 leading underscore...and so on
    >>> some_dict = {'a': 2, '_b':3, '__c':4, 'd': 5}
    >>> sort_dict_by_underscore_length(some_dict)
    [{'a': 2, 'd': 5}, {'_b': 3}, {'__c': 4}]
    """
    some_dict_keys = list(some_dict.keys())
    some_dict_keys_sorted = sort_keywords_by_underscore_length(some_dict_keys)

    sorted_list_of_dicts = [
        dict([(key, some_dict[key]) for key in list_of_args])
        for list_of_args in some_dict_keys_sorted
    ]

    return sorted_list_of_dicts


def sort_keywords_by_underscore_length(arg_keys: List[str]) -> List[List[str]]:
    """
    Sort other_arg_keys depending on their leading underscores

    Does not strip the underscores!
    >>> sort_keywords_by_underscore_length(['a', '_b', '__c', 'd'])
    [['a', 'd'], ['_b'], ['__c']]
    """

    dict_of_keys_and_underscore_counts = dict(
        [
            (key_value, count_leading_underscores_in_string(key_value))
            for key_value in arg_keys
        ]
    )
    count_underscore_values = list(dict_of_keys_and_underscore_counts.values())
    max_number_of_underscores = max(count_underscore_values)

    sorted_keywords = [
        [
            key
            for key, key_value in dict_of_keys_and_underscore_counts.items()
            if key_value == key_len
        ]
        for key_len in range(max_number_of_underscores + 1)
    ]

    return sorted_keywords


def count_leading_underscores_in_string(process_string: str) -> int:
    """
    How many underscores at start of process string

    """
    if len(process_string) == 0:
        raise Exception(
            "Can't pass a parameter name consisting only of underscores or a zero length string"
        )

    if process_string[0] == "_":
        return count_leading_underscores_in_string(process_string[1:]) + 1

    return 0


def strip_underscores_from_dict_keys(arg_dict: dict) -> dict:
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


def strip_leading_underscores_from_str(process_string: str) -> str:
    return re.sub("^[^A-Za-z]*", "", process_string)


def force_args_to_same_length(
    data_args_input: list, data: list, pad_with=arg_not_supplied
):
    """
    Ensure data_args is same length as data list, padding out if required
    """
    if pad_with is arg_not_supplied:
        pad_with = {}
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
            "WARNING: some unused data arguments passed when creating trading rule (had %d leftover, only needed %d)"
            % (len(data_args), len(data))
        )

    return padded_data_args


def camel_case_split(some_str: str) -> list:
    return re.split("(?<!^)(?=[A-Z])", some_str)
