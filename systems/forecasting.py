from copy import copy

from systems.stage import SystemStage
from syscore.objects import resolve_function, resolve_data_method, hasallattr
from systems.system_cache import input, diagnostic, output

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

    def __init__(self, trading_rules=None):
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

        :returns: Rules object

        """
        super().__init__()

        # We won't have trading rules we can use until we've parsed them
        setattr(self, "_trading_rules", None)

        # ... store the ones we've been passed for now
        setattr(self, "_passed_trading_rules", trading_rules)

    def _name(self):
        return "rules"

    def __repr__(self):
        trading_rules = self._trading_rules

        if trading_rules is not None:
            rule_names = ", ".join(self._trading_rules.keys())
            return "Rules object with rules " + rule_names

        else:
            return "Rules object with unknown trading rules [try Rules.tradingrules() ]"

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
        return (new_rules)

    @output()
    def get_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Does what it says on the tin - pulls the forecast for the trading rule

        This forecast will need scaling and capping later

        KEY OUTPUT

        """

        system = self.parent

        self.log.msg(
            "Calculating raw forecast %s for %s" % (instrument_code,
                                                    rule_variation_name),
            instrument_code=instrument_code,
            rule_variation_name=rule_variation_name)

        trading_rule = self.trading_rules()[rule_variation_name]

        result = trading_rule.call(system, instrument_code)
        result.columns = [rule_variation_name]

        return result


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
                     (Either passed in separately , or as part of a TradingRule, 3-tuple, or dict object)
        :type other_args: dict

        :returns: single Tradingrule object
        """

        if hasallattr(rule, ["function", "data", "other_args"]):
            # looks like it is already a trading rule
            (rule_function, data, other_args) = (rule.function, rule.data,
                                                 rule.other_args)

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
                rule_function = rule['function']
            except KeyError:
                raise Exception(
                    "If you specify a TradingRule as a dict it has to contain a 'function' keyname"
                )

            if "data" in rule:
                data = rule['data']
            else:
                data = []

            if "other_args" in rule:
                other_args = rule['other_args']

            else:
                other_args = dict()
        else:
            rule_function = rule

        # turn string into a callable function if required
        rule_function = resolve_function(rule_function)

        if isinstance(data, str):
            # turn into a 1 item list or wont' get parsed properly
            data = [data]

        setattr(self, "function", rule_function)
        setattr(self, "data", data)
        setattr(self, "other_args", other_args)

    def __repr__(self):
        data_names = ", ".join(self.data)
        args_names = ", ".join(self.other_args.keys())
        return "TradingRule; function: %s, data: %s and other_args: %s" % (
            str(self.function), data_names, args_names)

    def call(self, system, instrument_code):
        """
        Actually call a trading rule

        To do this we need some data from the system
        """

        assert isinstance(self.data, list)

        if len(self.data) == 0:
            # if no data provided defaults to using price
            datalist = [DEFAULT_PRICE_SOURCE]
        else:
            datalist = self.data

        data_methods = [
            resolve_data_method(system, data_string)
            for data_string in datalist
        ]
        data = [data_method(instrument_code) for data_method in data_methods]

        other_args = self.other_args

        return self.function(*data, **other_args)


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
        ans = dict([("rule%d" % ruleid, TradingRule(rule))
                    for (ruleid, rule) in enumerate(trading_rules)])
        return ans

    if isinstance(trading_rules, dict):
        if "function" not in trading_rules:
            # Note the system config will always come in as a dict
            ans = dict([(keyname, TradingRule(trading_rules[keyname]))
                        for keyname in trading_rules])
            return ans

    # Must be an individual rule (string, function, dict with 'function' or
    # tuple)
    return process_trading_rules([trading_rules])


def create_variations_oneparameter(baseRule,
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
        baseRule,
        list_of_args_dict,
        key_argname=argname,
        nameformat=nameformat)

    return ans


def create_variations(baseRule,
                      list_of_args_dict,
                      key_argname=None,
                      nameformat="%s_%s"):
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
                "Argname %s missing from at least one set of argument values" %
                key_argname)

        # these will be overwritten or added to as we run through
        baseRuleargs = copy(baseRule.other_args)

        for arg_name in args_dict.keys():
            baseRuleargs[arg_name] = args_dict[arg_name]

        rule_variation = TradingRule(baseRulefunction, baseRuledata,
                                     baseRuleargs)
        var_name = nameformat % (key_argname, str(args_dict[key_argname]))

        variations[var_name] = rule_variation

    return variations


if __name__ == '__main__':
    import doctest
    doctest.testmod()
