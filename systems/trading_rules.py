from copy import copy

import pandas as pd

from syscore.objects import (
    resolve_data_method,
    resolve_function,
    hasallattr,
)
from syscore.constants import arg_not_supplied
from syscore.pandas.strategy_functions import replace_all_zeros_with_nan
from syscore.text import (
    sort_dict_by_underscore_length,
    strip_underscores_from_dict_keys,
    force_args_to_same_length,
)

DEFAULT_PRICE_SOURCE = "data.daily_prices"


class TradingRule(object):
    """
    Container for trading rules

    Can be called manually or will be called when configuring a system
    """

    def __init__(
        self, rule, data: list = arg_not_supplied, other_args: dict = arg_not_supplied
    ):
        """
        Create a trading rule from a function

        Functions must be of the form function(*dataargs, **kwargs), where
        *dataargs are unnamed data items, and **kwargs are named configuration
        items data, an ordered list of strings identifying data to be used
        (default, just price) other_args: a dictionary of named arguments to be
        passed to the trading rule

        :param rule: Trading rule to be created
        :type trading_rules:
            The following describe a rule completely (ignore data and other_args arguments)
                3-tuple ; containing (function, data, other_args)
                dict (containing key "function", and optionally keys "other_args" and "data")
                TradingRule (object is created out of this rule)


            The following will be combined with the data and other_args arguments
            to produce a complete TradingRule:

                Other callable function
                str (with path to function eg
                "systems.provide.example.rules.ewmac_forecast_with_defaults")

        :param data: (list of) str pointing to location of inputs in a system method call (eg "data.get_instrument_price")
                     (Either passed in separately, or as part of a TradingRule, 3-tuple, or dict object)
        :type data: single str, or list of str

        :param other_args: Other named arguments to be passed to trading rule function
                    Any arguments that are prefixed with "_" will be passed to the first data function call
                    Any arguments that are prefixed with "__" will be passed to the second data function call... and so on
                     (Either passed in separately , or as part of a TradingRule, 3-tuple, or dict object)

        :type other_args: dict

        :returns: single Tradingrule object
        """

        rule_components = _get_trading_rule_components_depending_on_rule_input(
            rule, data=data, other_args=other_args
        )

        # fill the object with the components we need
        self._function = rule_components.function
        self._data = rule_components.data
        self._other_args = rule_components.other_args
        self._data_args = rule_components.data_args

    @property
    def function(self):
        return self._function

    @property
    def data(self):
        return self._data

    @property
    def other_args(self):
        return self._other_args

    @property
    def data_args(self):
        return self._data_args

    def __repr__(self):
        return _repr_trading_rule(self)

    def call(self, system: "System", instrument_code: str) -> pd.Series:
        """
        Actually call a trading rule

        To do this we need some data from the system
        """

        list_of_data_for_call = self._get_data_from_system(system, instrument_code)
        result = self._call_with_data(list_of_data_for_call)

        # Check for all zeros
        result = replace_all_zeros_with_nan(result)

        return result

    def _get_data_from_system(self, system: "System", instrument_code: str):
        """
        Prepare the data for a function call

        :param system: A system
        :param instrument_code: str
        :return: list of data
        """

        # Following is a list of additional kwargs to pass to the data functions. Can be empty dicts
        # Use copy as can be overridden

        list_of_data_str_references = self.data
        list_of_args_to_pass_to_data_calls = copy(self.data_args)

        list_of_data_methods = self._get_data_methods_from_list_of_data_string(
            list_of_data_str_references=list_of_data_str_references, system=system
        )

        list_of_data_for_call = self._get_data_from_list_of_methods_and_arguments(
            instrument_code=instrument_code,
            list_of_args_to_pass_to_data_calls=list_of_args_to_pass_to_data_calls,
            list_of_data_methods=list_of_data_methods,
        )

        return list_of_data_for_call

    def _get_data_methods_from_list_of_data_string(
        self, list_of_data_str_references: list, system
    ) -> list:
        # Turn a list of strings into a list of function objects
        list_of_data_methods = [
            resolve_data_method(system, data_string)
            for data_string in list_of_data_str_references
        ]

        return list_of_data_methods

    def _get_data_from_list_of_methods_and_arguments(
        self,
        instrument_code: str,
        list_of_data_methods: list,
        list_of_args_to_pass_to_data_calls: list,
    ) -> list:
        # Call the functions, providing additional data if neccesssary
        list_of_data_for_call = [
            data_method(instrument_code, **data_arguments)
            for data_method, data_arguments in zip(
                list_of_data_methods, list_of_args_to_pass_to_data_calls
            )
        ]

        return list_of_data_for_call

    def _call_with_data(self, list_of_data_for_call: list) -> pd.Series:
        other_args = self.other_args
        result = self.function(*list_of_data_for_call, **other_args)
        return result


def _repr_trading_rule(rule: TradingRule):
    data = rule.data
    data_args = rule.data_args
    other_arg_names = list(rule.other_args.keys())
    function = rule.function

    data_names = [
        "%s (args: %s)" % (data_name, str(data_arg))
        for data_name, data_arg in zip(data, data_args)
    ]
    data_names = ", ".join(data_names)
    args_names = ", ".join(other_arg_names)

    return "TradingRule; function: %s, data: %s and other_args: %s" % (
        str(function),
        data_names,
        args_names,
    )


class tradingRuleComponents(object):
    def __init__(
        self,
        rule_function: "function",
        data: list,
        other_args: dict,
        data_args: list = arg_not_supplied,
    ):
        rule_function, data, other_args, data_args = self._process_inputs(
            rule_function=rule_function,
            data=data,
            other_args=other_args,
            data_args=data_args,
        )

        self._data = data
        self._other_args = other_args
        self._data_args = data_args

        self._check_values()

    def _process_inputs(
        self,
        rule_function: "function",
        data: list,
        other_args: dict,
        data_args: list = arg_not_supplied,
    ):
        # turn string into a callable function if required
        self._rule_function = resolve_function(rule_function)

        if isinstance(data, str):
            # turn into a 1 item list or wont' get parsed properly
            data = [data]

        if len(data) == 0:
            if data_args is not arg_not_supplied:
                print("WARNING! Ignoring data_args as data is list length zero")
            # if no data provided defaults to using price
            data = [DEFAULT_PRICE_SOURCE]
            data_args = [{}]

        if data_args is arg_not_supplied:
            # This will be the case if the rule was built from arguments
            # Resolve any _ prefixed other_args
            other_args, data_args = _separate_other_args(other_args, data)

        return rule_function, data, other_args, data_args

    @property
    def function(self):
        return self._rule_function

    @property
    def data(self) -> list:
        return self._data

    @property
    def data_args(self) -> list:
        return self._data_args

    @property
    def other_args(self) -> dict:
        return self._other_args

    def _check_values(self):
        assert isinstance(self.data, list)
        assert isinstance(self.data_args, list)
        assert isinstance(self.other_args, dict)
        assert len(self.data) == len(self.data_args)


def _get_trading_rule_components_depending_on_rule_input(
    rule, data: list, other_args: dict
) -> tradingRuleComponents:
    if data is arg_not_supplied:
        data = []

    if other_args is arg_not_supplied:
        other_args = {}

    if _already_a_trading_rule(rule):
        # looks like it is already a trading rule
        rule_components = _create_rule_from_existing_rule(
            rule, data=data, other_args=other_args
        )

    elif isinstance(rule, tuple):
        rule_components = _create_rule_from_tuple(
            rule, data=data, other_args=other_args
        )

    elif isinstance(rule, dict):
        rule_components = _create_rule_from_dict(rule, data=data, other_args=other_args)
    else:
        rule_components = _create_rule_from_passed_elements(
            rule, data=data, other_args=other_args
        )

    return rule_components


def _already_a_trading_rule(rule):
    return hasallattr(rule, ["function", "data", "other_args"])


def _create_rule_from_existing_rule(
    rule, data: list, other_args: dict
) -> tradingRuleComponents:
    _throw_warning_if_passed_rule_and_data(
        "tradingRule", data=data, other_args=other_args
    )
    return tradingRuleComponents(
        rule_function=rule.function,
        data=rule.data,
        other_args=rule.other_args,
        data_args=rule.data_args,
    )


def _throw_warning_if_passed_rule_and_data(
    type_of_rule_passed: str, data: list, other_args: dict
):
    if len(data) > 0 or len(other_args) > 0:
        print(
            "WARNING: Creating trade rule with 'rule' type %s argument, ignoring data and/or other args"
            % type_of_rule_passed
        )


def _create_rule_from_tuple(rule, data: list, other_args: dict):
    _throw_warning_if_passed_rule_and_data("tuple", data=data, other_args=other_args)

    if len(rule) != 3:
        raise Exception(
            "Creating trading rule with a tuple, must be length 3 exactly (function/name, data [...], args dict(...))"
        )
    (rule_function, data, other_args) = rule

    rule_components = tradingRuleComponents(
        rule_function=rule_function, data=data, other_args=other_args
    )

    return rule_components


def _create_rule_from_dict(rule, data: list, other_args: dict) -> tradingRuleComponents:
    _throw_warning_if_passed_rule_and_data("dict", data=data, other_args=other_args)

    try:
        rule_function = rule["function"]
    except KeyError:
        raise Exception(
            "If you specify a TradingRule as a dict it has to contain a 'function' keyname"
        )

    data = rule.get("data", [])
    other_args = rule.get("other_args", {})

    rule_components = tradingRuleComponents(
        data=data, rule_function=rule_function, other_args=other_args
    )

    return rule_components


def _create_rule_from_passed_elements(
    rule, data: list, other_args: dict
) -> tradingRuleComponents:
    rule_components = tradingRuleComponents(
        rule_function=rule, data=data, other_args=other_args
    )

    return rule_components


def _separate_other_args(other_args: dict, data: list) -> tuple:
    """
    Separate out other arguments into those passed to the trading rule function, and any
     that will be passed to the data functions (data_args)

    :param other_args: dict containing args. Some may have "_" prefix of various lengths, these are data args
    :param data: list of str pointing to where data lives. data_args has to be the same length as this

    :return: tuple. First element is other_args dict to pass to main function.
            Second element is list, each element of which is a dict to data functions
            List is same length as data
            Lists may consist of empty dicts to pad in case earlier data functions have no entries
    """

    # Split arguments up into groups depending on number of leading _
    # 0 (passed as other_args to data function), 1, 2, 3 ...
    if len(other_args) == 0:
        return ({}, [{}] * len(data))

    sorted_other_args = sort_dict_by_underscore_length(other_args)

    # The first item in the list has no underscores, and is for the main
    # trading rule function
    other_args_for_trading_rule = sorted_other_args.pop(0)

    # The rest are data_args. At this point the key values still have "_" so
    # let's drop them
    data_args = [
        strip_underscores_from_dict_keys(arg_dict) for arg_dict in sorted_other_args
    ]

    # Force them to be the same length so things don't break later
    # Pad if required
    data_args_forced_to_length = force_args_to_same_length(data_args, data)
    assert len(data) == len(data_args_forced_to_length)

    return other_args_for_trading_rule, data_args_forced_to_length


def create_variations_oneparameter(baseRule, list_of_args, argname, nameformat="%s_%s"):
    """
    Returns a dict of trading rule variations, varying only one named parameter

    :param baseRule: Trading rule to copy
    :type baseRule: TradingRule object

    :param list_of_args: set of parameters to use
    :type list_of_args: list

    :param argname: Argument passed to trading rule which will be changed
    :type argname: str

    :param nameformat: Format to use when naming trading rules; nameformat % (argname, argvalue) will be used
    :type nameformat: str containing two '%s' elements

    :returns: dict of Tradingrule objects

    >>>
    >>> rule=TradingRule(("systems.provided.rules.ewmac.ewmac_forecast_with_defaults", [], {}))
    >>> variations=create_variations_oneparameter(rule, [4,10,100], "Lfast")
    >>> ans=list(variations.keys())
    >>> ans.sort()
    >>> ans
    ['Lfast_10', 'Lfast_100', 'Lfast_4']
    """
    list_of_args_dict = []
    for arg_value in list_of_args:
        thisdict = dict()
        thisdict[argname] = arg_value
        list_of_args_dict.append(thisdict)

    ans = create_variations(
        baseRule, list_of_args_dict, key_argname=argname, nameformat=nameformat
    )

    return ans


def create_variations(
    baseRule, list_of_args_dict, key_argname=None, nameformat="%s_%s"
):
    """
    Returns a dict of trading rule variations

    eg create_variations(ewmacrule, [dict(fast=2, slow=8), dict(fast=4, ...) ], argname="fast", basename="ewmac")


    :param baseRule: Trading rule to copy
    :type baseRule: TradingRule object

    :param list_of_args_dict:  sets of parameters to use.
    :type list_of_args: list of dicts; each dict contains a set of parameters to vary for each instance

    :param key_argname: Non
    :type key_argname: str or None (None is allowed if only one parameter is changed)

    :param nameformat: Format to use when naming trading rules; nameformat % (argname, argvalue) will be used
    :type nameformat: str containing two '%s' elements

    :returns: dict of Tradingrule objects

    >>> rule=TradingRule(("systems.provided.rules.ewmac.ewmac_forecast_with_defaults", [], {}))
    >>> variations=create_variations(rule, [dict(Lfast=2, Lslow=8), dict(Lfast=4, Lslow=16)], "Lfast", nameformat="ewmac_%s_%s")
    >>> ans=list(variations.keys())
    >>> ans.sort()
    >>> ans
    ['ewmac_Lfast_2', 'ewmac_Lfast_4']
    """

    if key_argname is None:
        if all([len(args_dict) == 1 for args_dict in list_of_args_dict]):
            # okay to use argname as only seems to be one of them
            key_argname = list_of_args_dict[0].keys()[0]
        else:
            raise Exception("need to specify argname if more than one possibility")

    baseRulefunction = baseRule.function
    baseRuledata = baseRule.data

    variations = dict()

    for args_dict in list_of_args_dict:
        if key_argname not in args_dict.keys():
            raise Exception(
                "Argname %s missing from at least one set of argument values"
                % key_argname
            )

        # these will be overwritten or added to as we run through
        baseRuleargs = copy(baseRule.other_args)

        for arg_name in args_dict.keys():
            baseRuleargs[arg_name] = args_dict[arg_name]

        rule_variation = TradingRule(baseRulefunction, baseRuledata, baseRuleargs)
        var_name = nameformat % (key_argname, str(args_dict[key_argname]))

        variations[var_name] = rule_variation

    return variations
