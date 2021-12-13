import numpy as np
from systems.system_cache import output
from systems.accounts.account_instruments import accountInstruments
from systems.accounts.curves.dict_of_account_curves import dictOfAccountCurves
from systems.accounts.curves.account_curve_group import accountCurveGroup


class accountPortfolio(accountInstruments):
    @output(not_pickable=True)
    def portfolio(self, delayfill=True, roundpositions=True):
        """
        Get the p&l for entire portfolio

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.portfolio().ann_std()
        0.2638225179274214
        """

        self.log.terse("Calculating pandl for portfolio")
        capital = self.get_notional_capital()
        instruments = self.get_instrument_list()
        dict_of_pandl_by_instrument = dict(
            [
                (
                    instrument_code,
                    self.pandl_for_instrument(
                        instrument_code,
                        delayfill=delayfill,
                        roundpositions=roundpositions,
                    ),
                )
                for instrument_code in instruments
            ]
        )

        dict_of_pandl_by_instrument = dictOfAccountCurves(dict_of_pandl_by_instrument)

        account_curve = accountCurveGroup(
            dict_of_pandl_by_instrument, capital=capital, weighted=True
        )

        return account_curve

    @output()
    def total_portfolio_level_turnover(self, roundpositions=True):
        list_of_instruments = self.get_instrument_list()
        list_of_turnovers_at_portfolio_level = [
            self.turnover_at_portfolio_level(
                instrument_code, roundpositions=roundpositions
            )
            for instrument_code in list_of_instruments
        ]

        total_turnover = np.nansum(list_of_turnovers_at_portfolio_level)

        return total_turnover
