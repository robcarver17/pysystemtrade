import numpy as np

from copy import copy
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from systems.stage import SystemStage
from syscore.objects import resolve_function, resolve_data_method, hasallattr
from syscore.text import (
    sort_dict_by_underscore_length,
    strip_underscores_from_dict_keys,
    force_args_to_same_length,
)

from systems.system_cache import input, diagnostic, output, dont_cache

DEFAULT_PRICE_SOURCE = "data.daily_prices"


class Rules(SystemStage):
    """
    Construct the forecasting stage

    Ways we can do this:

    a) We do this by passing a list of trading rules

    forecasting([trading_rule1, trading_rule2, ..])

    Note that trading rules can be created using the TradingRule class, or you
      can just pass in the name of a function, or a function.

    We can also use a generate_variations method to create a list of multiple
      rules

    b) or we can create from a system config


    KEY INPUT: Depends on trading rule(s) data argument
    KEY OUTPUT: system.rules.get_raw_forecast(instrument_code, rule_variation_name)
                system.rules.trading_rules()

    Name: rules
    """

    def __init__(self, trading_rules=None, pre_calc_rules=True):
        """
        Create a SystemStage for forecasting

        We either pass a dict or a list of trading rules (functions, strings
          specifying a function, or objects of class TradingRule)
          ... or we'll get it from the overall system config
          (trading_rules=None)

        :param trading_rules: Set of trading rules
        :type trading_rules: None (rules will be inherited from self.parent
          system) TradingRule, str, callable function, or tuple (single rule)
          list or dict (multiple rules)
        :param pre_calc_rules: bool, if True then the first call to get a rule will calculate the values for all markets

        :returns: Rules object

        """
        super().__init__()

        # We won't have trading rules we can use until we've parsed them
        setattr(self, "_trading_rules", None)

        # ... store the ones we've been passed for now
        setattr(self, "_passed_trading_rules", trading_rules)

        # PRE CALC NOT IMPLEMENTED THESE ARE IRRELEVANT
        self.pre_calc_rules = pre_calc_rules
        self._pre_calculation_not_yet_done = True

    def _name(self):
        return "rules"

    def __repr__(self):
        trading_rules = self.trading_rules()

        rule_names = ", ".join(trading_rules.keys())

        return "Rules object with rules " + rule_names

    @dont_cache
    def trading_rules(self):
        """
        Ensure self.trading_rules is actually a properly specified list of trading rules

        We can't do this when we __init__ because we might not have a parent yet

        :returns: List of TradingRule objects

        """

        current_rules = self._trading_rules

        # We have already parsed the trading rules for this object, just return
        # them
        if current_rules is not None:
            return current_rules

        # What where we passed when object was created?
        passed_rules = self._passed_trading_rules

        if passed_rules is None:
            """
            We weren't passed anything in the command lines so need to inherit from the system config
            """

            if not hasattr(self, "parent"):
                error_msg = "A Rules stage needs to be part of a System to identify trading rules, unless rules are passed when object created"
                self.log.critical(error_msg)

            if not hasattr(self.parent, "config"):
                error_msg = "A system needs to include a config with trading_rules, unless rules are passed when object created"
                self.log.critical(error_msg)

            if not hasattr(self.parent.config, "trading_rules"):
                error_msg = "A system config needs to include trading_rules, unless rules are passed when object created"
                self.log.critical(error_msg)

            # self.parent.config.tradingrules will already be in dictionary
            # form
            forecasting_config = self.parent.config.trading_rules
            new_rules = process_trading_rules(forecasting_config)

        else:

            # Okay, we've been passed a list manually which we'll use rather
            # than getting it from the system
            new_rules = process_trading_rules(passed_rules)

        setattr(self, "_trading_rules", new_rules)
        """
        if self.pre_calc_rules and self._pre_calculation_not_yet_done:
            # Pre calculate all values for all rules, and drop into the cache
            # This is especially fast if we're using parallel processing
            all_rule_names = new_rules.keys()
            for rule_name in all_rule_names:
                self._precalc_forecasts_for_rule_all_instruments_and_cache(rule_name)

            # so we don't do this again
            self._pre_calculation_not_yet_done = False
        """

        return new_rules

    @output()
    def get_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Does what it says on the tin - pulls the forecast for the trading rule

        This forecast will need scaling and capping later

        KEY OUTPUT

        """

        system = self.parent

        self.log.msg(
            "Calculating raw forecast %s for %s"
            % (instrument_code, rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name,
        )

        trading_rule = self.trading_rules()[rule_variation_name]

        result = trading_rule.call(system, instrument_code)
        result.columns = [rule_variation_name]

        # Check for all zeros
        check_result = copy(result)
        check_result[check_result == 0.0] = np.nan
        if all(check_result.isna()):
            self.log.warn(
                "Setting rule %s for %s to all NAN as all values are 0 or NAN"
                % (instrument_code, rule_variation_name)
            )
            result[:] = np.nan

        return result

    @dont_cache
    def _precalc_forecasts_for_rule_all_instruments_and_cache(
        self, rule_variation_name
    ):
        """
        Pre calculate all values for all instrument, and drop into the cache
        This is especially fast if we're using parallel processing

        :param rule_variation_name: str
        :return: None (results dumped into the cache)
        """

        self.log.msg("Pre-calculating forecast rule values")

        trading_rule = self.trading_rules()[rule_variation_name]
        system = self.parent
        parallel_processing = system.process_pool
        max_workers = system.process_pool_max_workers

        rule_function = trading_rule.function
        instrument_list = system.get_instrument_list()

        rule_data_as_list_across_instruments = [
            trading_rule.get_data_from_system(system, instrument_code)
            for instrument_code in instrument_list
        ]
        other_args_as_dict = trading_rule.other_args

        partial_function = partial(
            _function_call_with_args,
            function=rule_function,
            other_args_as_dict=other_args_as_dict,
        )

        if parallel_processing:
            # Parallel version
            # FIXME: NOT WORKING
            """
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                instrument_forecasts = executor.map(partial_function, rule_data_as_list_across_instruments)
            """
            # FIXME USE NON PARALLEL INSTEAD FOR NOW
            instrument_forecasts = [
                partial_function(this_instrument_data)
                for this_instrument_data in rule_data_as_list_across_instruments
            ]

        else:

            # Non parallel version
            instrument_forecasts = [
                partial_function(this_instrument_data)
                for this_instrument_data in rule_data_as_list_across_instruments
            ]

        # Add to cache
        for instrument_code, forecast_this_instrument in zip(
            instrument_list, instrument_forecasts
        ):
            cache_ref = system.cache.cache_ref(
                self.get_raw_forecast, self, instrument_code, rule_variation_name)

            system.cache.set_item_in_cache(forecast_this_instrument, cache_ref)


def function_call_with_args(
        data_as_list,
        function=None,
        other_args_as_dict={}):
    # convenience function to make creating a parital easier
    return function(*data_as_list, **other_args_as_dict)


class TradingRule(object):
    """
    Container for trading rules

    Can be called manually or will be called when configuring a system
    """

    def __init__(self, rule, data=list(), other_args=dict()):
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

        data_args = None

        if hasallattr(rule, ["function", "data", "other_args"]):
            # looks like it is already a trading rule
            (rule_function, data, other_args, data_args) = (
                rule.function,
                rule.data,
                rule.other_args,
                rule.data_args,
            )

        elif isinstance(rule, tuple):
            if len(data) > 0 or len(other_args) > 0:
                print(
                    "WARNING: Creating trade rule with 'rule' tuple argument, ignoring data and/or other args"
                )

            if len(rule) != 3:
                raise Exception(
                    "Creating trading rule with a tuple, must be length 3 exactly (function/name, data [...], args dict(...))"
                )
            (rule_function, data, other_args) = rule

        elif isinstance(rule, dict):
            if len(data) > 0 or len(other_args) > 0:
                print(
                    "WARNING: Creating trade rule with 'rule' dict argument, ignoring data and/or other args"
                )

            try:
                rule_function = rule["function"]
            except KeyError:
                raise Exception(
                    "If you specify a TradingRule as a dict it has to contain a 'function' keyname"
                )

            if "data" in rule:
                data = rule["data"]
            else:
                data = []

            if "other_args" in rule:
                other_args = rule["other_args"]

            else:
                other_args = dict()
        else:
            rule_function = rule

        # turn string into a callable function if required
        rule_function = resolve_function(rule_function)

        if isinstance(data, str):
            # turn into a 1 item list or wont' get parsed properly
            data = [data]

        if data_args is None:
            # This will be the case if the rule was built from arguments
            # Resolve any _ prefixed other_args
            other_args, data_args = separate_other_args(other_args, data)

        # fill the object with data
        setattr(self, "function", rule_function)
        setattr(self, "data", data)
        setattr(self, "other_args", other_args)
        setattr(self, "data_args", data_args)

    def __repr__(self):
        data_names = [
            "%s (args: %s)" % (data_name, str(data_args))
            for data_name, data_args in zip(self.data, self.data_args)
        ]
        data_names = ", ".join(data_names)
        args_names = ", ".join(self.other_args.keys())

        return "TradingRule; function: %s, data: %s and other_args: %s" % (
            str(self.function),
            data_names,
            args_names,
        )

    def call(self, system, instrument_code):
        """
        Actually call a trading rule

        To do this we need some data from the system
        """

        data = self.get_data_from_system(system, instrument_code)
        result = self.call_with_data(data)

        return result

    def get_data_from_system(self, system, instrument_code):
        """
        Prepare the data for a function call

        :param system: A system
        :param instrument_code: str
        :return: list of data
        """
        data = self.data
        assert isinstance(data, list)

        # Following is a list of additional kwargs to pass to the data functions. Can be empty dicts
        # Use copy as can be overriden

        if len(data) == 0:
            # if no data provided defaults to using price
            datalist = [DEFAULT_PRICE_SOURCE]
            data_arg_list = [{}]
        else:
            # We're provided with a list
            datalist = self.data
            data_arg_list = copy(self.data_args)

        # This is so the zip won't unexpectedly fail
        # Should be the case given how data_args are generated
        assert len(data_arg_list) == len(datalist)

        # Turn a list of strings into a list of function objects
        data_methods = [
            resolve_data_method(
                system,
                data_string) for data_string in datalist]

        # Call the functions, providing additional data if neccesssary
        data = [
            data_method(instrument_code, **data_arguments)
            for data_method, data_arguments in zip(data_methods, data_arg_list)
        ]

        return data

    def call_with_data(self, data):
        other_args = self.other_args

        return self.function(*data, **other_args)


def separate_other_args(other_args, data):
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
    data_args = [strip_underscores_from_dict_keys(
        arg_dict) for arg_dict in sorted_other_args]

    # Force them to be the same length so things don't break later
    # Pad if required
    data_args_forced_to_length = force_args_to_same_length(data_args, data)
    assert len(data) == len(data_args_forced_to_length)

    return other_args_for_trading_rule, data_args_forced_to_length


def process_trading_rules(trading_rules):
    """

    There are a number of ways to specify a set of trading rules. This function processes them all,
       and returns a dict of TradingRule objects.

    data types handled:
       dict - parse each element of the dict and use the names [unless has one or more of keynames: function, data, args]
       list - parse each element of the list and give them arbitrary names
       anything else is assumed to be something we can pass to TradingRule (string, function, tuple, (dict with keynames function, data, args), or TradingRule object)


    :param trading_rules: Set of trading rules

    :type trading_rules:    Single rule:
                            dict(function=str, optionally: args=dict(), optionally: data=list()),
                            TradingRule, str, callable function, or tuple

                            Multiple rules:
                            list, dict without 'function' keyname

    :returns: dict of Tradingrule objects

    """
    if isinstance(trading_rules, list):
        # Give some arbitrary name
        ans = dict(
            [
                ("rule%d" % ruleid, TradingRule(rule))
                for (ruleid, rule) in enumerate(trading_rules)
            ]
        )
        return ans

    if isinstance(trading_rules, dict):
        if "function" not in trading_rules:
            # Note the system config will always come in as a dict
            ans = dict(
                [
                    (keyname, TradingRule(trading_rules[keyname]))
                    for keyname in trading_rules
                ]
            )
            return ans

    # Must be an individual rule (string, function, dict with 'function' or
    # tuple)
    return process_trading_rules([trading_rules])


def create_variations_oneparameter(
        baseRule,
        list_of_args,
        argname,
        nameformat="%s_%s"):
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
    >>> rule=TradingRule(("systems.provided.example.rules.ewmac_forecast_with_defaults", [], {}))
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

    >>> rule=TradingRule(("systems.provided.example.rules.ewmac_forecast_with_defaults", [], {}))
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
            raise Exception(
                "need to specify argname if more than one possibility")

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

        rule_variation = TradingRule(
            baseRulefunction, baseRuledata, baseRuleargs)
        var_name = nameformat % (key_argname, str(args_dict[key_argname]))

        variations[var_name] = rule_variation

    return variations


if __name__ == "__main__":
    import doctest

    doctest.testmod()
