import pandas as pd

from systems.stage import SystemStage
from syscore.objects import arg_not_supplied

from systems.system_cache import  output, dont_cache
from systems.trading_rules import TradingRule



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

    def __init__(self, trading_rules=arg_not_supplied):
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
        self._trading_rules = None

        # ... store the ones we've been passed for now
        self._passed_trading_rules = trading_rules


    @property
    def name(self):
        return "rules"

    @property
    def passed_trading_rules(self):
        return self._passed_trading_rules

    def __repr__(self):
        trading_rules = self.trading_rules()

        rule_names = ", ".join(trading_rules.keys())

        return "Rules object with rules " + rule_names


    @output()
    def get_raw_forecast(self, instrument_code: str,
                         rule_variation_name: str) -> pd.Series:
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
        # this will process all the rules, if not already done
        trading_rule_dict = self.trading_rules()
        trading_rule = trading_rule_dict[rule_variation_name]

        result = trading_rule.call(system, instrument_code)
        result = pd.Series(result)

        return result


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

        trading_rules = self._get_trading_rules_from_passed_rules()
        self._trading_rules = trading_rules

        return trading_rules

    def _get_trading_rules_from_passed_rules(self):

        # What where we passed when object was created?
        passed_rules = self.passed_trading_rules

        if passed_rules is arg_not_supplied:
            passed_rules = self._get_rules_from_parent_or_raise_errors()

        new_rules = process_trading_rules(passed_rules)

        return new_rules

    @dont_cache
    def _get_rules_from_parent_or_raise_errors(self):
        """
        We weren't passed anything in the command lines so need to inherit from the system config
        """
        error_msg = None
        if not hasattr(self, "parent"):
            error_msg = "A Rules stage needs to be part of a System to identify trading rules, unless rules are passed when object created"

        elif not hasattr(self.parent, "config"):
            error_msg = "A system needs to include a config with trading_rules, unless rules are passed when object created"

        elif not hasattr(self.parent.config, "trading_rules"):
            error_msg = "A system config needs to include trading_rules, unless rules are passed when object created"

        if error_msg is not None:
            self.log.critical(error_msg)
            raise Exception(error_msg)

        # self.parent.config.tradingrules will already be in dictionary
        # form
        forecasting_config_rules = self.parent.config.trading_rules

        return forecasting_config_rules


def process_trading_rules(passed_rules) -> dict:
    """

    There are a number of ways to specify a set of trading rules. This function processes them all,
       and returns a dict of TradingRule objects.

    data types handled:
       dict - parse each element of the dict and use the names [unless has one or more of keynames: function, data, args]
       list - parse each element of the list and give them arbitrary names
       anything else is assumed to be something we can pass to TradingRule (string, function, tuple, (dict with keynames function, data, args), or TradingRule object)


    :param passed_rules: Set of trading rules

    :type passed_rules:    Single rule:
                            dict(function=str, optionally: args=dict(), optionally: data=list()),
                            TradingRule, str, callable function, or tuple

                            Multiple rules:
                            list, dict without 'function' keyname

    :returns: dict of Tradingrule objects

    """
    if isinstance(passed_rules, list):
        # Give some arbitrary name
        processed_rules = _process_trading_rules_in_list(passed_rules)

    elif _is_a_single_trading_rule_in_a_dict(passed_rules):
        processed_rules = _process_single_trading_rule(passed_rules)

    elif _is_a_dict_of_multiple_trading_rules(passed_rules):
        processed_rules = _process_dict_of_trading_rules(passed_rules)

    else:
        # Must be an individual rule (string, function, dict with 'function' or
        # tuple)
        processed_rules = _process_single_trading_rule(passed_rules)

    return processed_rules

def _process_trading_rules_in_list(trading_rules: list):
    processed_rules = dict(
        [
            ("rule%d" % ruleid, TradingRule(rule))
            for (ruleid, rule) in enumerate(trading_rules)
        ]
    )
    return processed_rules

def _is_a_single_trading_rule_in_a_dict(trading_rules: dict):
    if isinstance(trading_rules, dict):
        if "function" in trading_rules:
            return True

    return False


def _is_a_dict_of_multiple_trading_rules(trading_rules: dict):
    if isinstance(trading_rules, dict):
        if "function" not in trading_rules:
            return True

    else:
        return False


def _process_dict_of_trading_rules(trading_rules: dict):
    processed_rules = dict(
        [
            (keyname, TradingRule(trading_rules[keyname]))
            for keyname in trading_rules
        ]
    )
    return processed_rules

def _process_single_trading_rule(trading_rule):
    list_of_rules = [trading_rule]
    processed_rules = _process_trading_rules_in_list(list_of_rules)
    return processed_rules


if __name__ == "__main__":
    import doctest

    doctest.testmod()

