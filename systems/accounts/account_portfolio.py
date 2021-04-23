from systems.system_cache import diagnostic, output, dont_cache
from systems.accounts.account_costs import accountCosts
from systems.accounts.account_instruments import accountInstruments
from systems.accounts.pandl_calculators.pandl_SR_cost import pandlCalculationWithSRCosts
from systems.accounts.pandl_calculators.pandl_cash_costs import pandlCalculationWithCashCostsAndFills
from systems.accounts.curves.account_curve import accountCurve

class accountPortfolio(accountCosts, accountBuffering):

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
        port_pandl = [
            self.pandl_for_instrument(
                instrument_code, delayfill=delayfill, roundpositions=roundpositions
            )
            for instrument_code in instruments
        ]

        port_pandl = accountCurveGroup(
            port_pandl, instruments, capital=capital, weighted_flag=True
        )

        return port_pandl


