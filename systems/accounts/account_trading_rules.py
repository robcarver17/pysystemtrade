import pandas as pd

from syscore.constants import arg_not_supplied
from systems.system_cache import diagnostic
from systems.accounts.account_forecast import accountForecast
from systems.accounts.curves.dict_of_account_curves import (
    dictOfAccountCurves,
    nestedDictOfAccountCurves,
)
from systems.accounts.curves.account_curve_group import accountCurveGroup
from systems.accounts.curves.nested_account_curve_group import nestedAccountCurveGroup


class accountTradingRules(accountForecast):
    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule_weighted(
        self, rule_variation_name: str, delayfill: bool = True
    ) -> accountCurveGroup:

        list_of_instruments = self.get_instrument_list()
        dict_of_pandl_by_instrument = dict(
            [
                (
                    instrument_code,
                    self.pandl_for_instrument_forecast_weighted(
                        instrument_code=instrument_code,
                        rule_variation_name=rule_variation_name,
                        delayfill=delayfill,
                    ),
                )
                for instrument_code in list_of_instruments
            ]
        )

        dict_of_pandl_by_instrument = dictOfAccountCurves(dict_of_pandl_by_instrument)

        capital = self.get_notional_capital()

        account_curve = accountCurveGroup(
            dict_of_pandl_by_instrument, capital=capital, weighted=True
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule_unweighted(
        self, rule_variation_name: str, delayfill: bool = True
    ) -> accountCurveGroup:

        list_of_instruments = self.get_instrument_list()
        dict_of_pandl_by_instrument = dict(
            [
                (
                    instrument_code,
                    self.pandl_for_instrument_forecast(
                        instrument_code=instrument_code,
                        rule_variation_name=rule_variation_name,
                        delayfill=delayfill,
                    ),
                )
                for instrument_code in list_of_instruments
            ]
        )

        dict_of_pandl_by_instrument = dictOfAccountCurves(dict_of_pandl_by_instrument)

        capital = self.get_notional_capital()

        account_curve = accountCurveGroup(
            dict_of_pandl_by_instrument, capital=capital, weighted=False
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_trading_rule(
        self, rule_variation_name: str, delayfill: bool = True
    ) -> accountCurveGroup:

        #  If I want the performance of a given trading rule across individual
        #  instruments in isolation, then I need to take pandl_for_trading_rule_weighted
        #  and normalise it so that the returns are as a proportion of the sum of
        #  all the relevant
        #  forecast weight * FDM * instrument weight * IDM;
        #  this is equivalent to the rules risk contribution within the system

        # flag as weighted but actually semi-weighted
        list_of_instruments = self.get_instrument_list()
        dict_of_pandl_by_instrument = dict(
            [
                (
                    instrument_code,
                    self.pandl_for_instrument_forecast_weighted_within_trading_rule(
                        instrument_code,
                        rule_variation_name=rule_variation_name,
                        delayfill=delayfill,
                    ),
                )
                for instrument_code in list_of_instruments
            ]
        )

        dict_of_pandl_by_instrument = dictOfAccountCurves(dict_of_pandl_by_instrument)

        capital = self.get_notional_capital()

        account_curve = accountCurveGroup(
            dict_of_pandl_by_instrument, capital=capital, weighted=True
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_all_trading_rules(
        self, delayfill: bool = True
    ) -> nestedAccountCurveGroup:

        ## group of pandl_for_trading_rule_weighted
        list_of_rules = self.list_of_trading_rules()

        dict_of_pandl_by_rule = dict(
            [
                (rule, self.pandl_for_trading_rule_weighted(rule, delayfill=delayfill))
                for rule in list_of_rules
            ]
        )

        dict_of_pandl_by_rule = nestedDictOfAccountCurves(dict_of_pandl_by_rule)
        capital = self.get_notional_capital()

        account_curve = nestedAccountCurveGroup(
            dict_of_pandl_by_rule, capital=capital, weighted=True
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_all_trading_rules_unweighted(self, delayfill: bool = True):

        # group of pandl_for_trading_rule
        list_of_rules = self.list_of_trading_rules()

        dict_of_pandl_by_rule = dict(
            [
                (rule, self.pandl_for_trading_rule(rule, delayfill=delayfill))
                for rule in list_of_rules
            ]
        )

        dict_of_pandl_by_rule = nestedDictOfAccountCurves(dict_of_pandl_by_rule)
        capital = self.get_notional_capital()

        account_curve = nestedAccountCurveGroup(
            dict_of_pandl_by_rule, capital=capital, weighted=False
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_rules(
        self, instrument_code: str, delayfill: bool = True
    ) -> accountCurveGroup:

        # how all trading rules have done for a particular instrument, weighted
        list_of_rules = self.list_of_rules_for_code(instrument_code)
        dict_of_pandl_by_rule = dict(
            [
                (
                    rule_variation_name,
                    self.pandl_for_instrument_forecast_weighted(
                        instrument_code=instrument_code,
                        rule_variation_name=rule_variation_name,
                        delayfill=delayfill,
                    ),
                )
                for rule_variation_name in list_of_rules
            ]
        )

        dict_of_pandl_by_rule = dictOfAccountCurves(dict_of_pandl_by_rule)

        capital = self.get_notional_capital()

        account_curve = accountCurveGroup(
            dict_of_pandl_by_rule, capital=capital, weighted=True
        )

        return account_curve

    @diagnostic(not_pickable=True)
    def pandl_for_instrument_rules_unweighted(
        self,
        instrument_code: str,
        trading_rule_list=arg_not_supplied,
        delayfill: bool = True,
    ) -> accountCurveGroup:

        # (unweighted group - elements are pandl_for_instrument_forecast across trading rules)
        if trading_rule_list is arg_not_supplied:
            trading_rule_list = self.list_of_rules_for_code(instrument_code)
        dict_of_pandl_by_rule = dict(
            [
                (
                    rule_variation_name,
                    self.pandl_for_instrument_forecast(
                        instrument_code=instrument_code,
                        rule_variation_name=rule_variation_name,
                        delayfill=delayfill,
                    ),
                )
                for rule_variation_name in trading_rule_list
            ]
        )

        dict_of_pandl_by_rule = dictOfAccountCurves(dict_of_pandl_by_rule)

        capital = self.get_notional_capital()

        account_curve = accountCurveGroup(
            dict_of_pandl_by_rule, capital=capital, weighted=False
        )

        return account_curve
