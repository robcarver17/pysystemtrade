from systems.system_cache import diagnostic, output, dont_cache
from systems.accounts.account_costs import accountCosts
from systems.accounts.accounts_buffering import accountBuffering
from systems.accounts.pandl_calculators.pandl_SR_cost import pandlCalculationWithSRCosts
from systems.accounts.pandl_calculators.pandl_cash_costs import pandlCalculationWithCashCostsAndFills
from systems.accounts.curves.account_curve import accountCurve

class accountInstruments(accountCosts, accountBuffering):
    @dont_cache
    def pandl_for_instrument(
        self, instrument_code:str,
            delayfill: bool=True,
            roundpositions: bool=True
    ) -> accountCurve:
        """
        Get the p&l for one instrument

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>> system.accounts.pandl_for_instrument("US10").ann_std()
        0.13908407620762306
        """

        self.log.msg(
            "Calculating pandl for instrument for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        use_SR_costs = self.use_SR_costs
        if use_SR_costs:
            instrument_pandl = self._pandl_for_instrument_with_SR_costs(instrument_code,
                                                                        roundpositions=roundpositions,
                                                                        delayfill=delayfill)
        else:
            instrument_pandl = self._pandl_for_instrument_with_cash_costs(instrument_code,
                                                                          roundpositions=roundpositions,
                                                                          delayfill=delayfill)

        return instrument_pandl

    @diagnostic(not_pickable=True)
    def _pandl_for_instrument_with_SR_costs(
            self, instrument_code: str,
            delayfill: bool = True,
            roundpositions: bool = True
    ) -> accountCurve:

        price = self.get_daily_price(instrument_code)
        positions = self.get_buffered_position(
            instrument_code, roundpositions=roundpositions
        )
        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_block_price_move(instrument_code)
        daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code
        )

        capital = self.get_notional_capital()

        SR_cost_per_trade = self.get_SR_cost_per_trade_for_instrument(instrument_code)
        instrument_turnover = self.instrument_turnover(
                instrument_code, roundpositions=roundpositions
            )
        annualised_SR_cost = SR_cost_per_trade * instrument_turnover

        average_position = self.get_average_position_for_instrument_at_portfolio_level(instrument_code)

        pandl_calculator = pandlCalculationWithSRCosts(price,
                                                       SR_cost=annualised_SR_cost,
                                                       positions=positions,
                                                       average_position=average_position,
                                                       daily_returns_volatility=daily_returns_volatility,
                                                       capital=capital,
                                                       value_per_point=value_of_price_point,
                                                       delayfill=delayfill,
                                                       fx=fx,
                                                       roundpositions=roundpositions)

        account_curve = accountCurve(pandl_calculator, weighted=True)

        return account_curve

    @diagnostic(not_pickable=True)
    def _pandl_for_instrument_with_cash_costs(
            self, instrument_code: str,
            delayfill: bool = True,
            roundpositions: bool = True
    ) -> accountCurve:

        if not roundpositions:
            self.log.warn("Using roundpositions=False with cash costs may lead to inaccurate costs (fixed costs, eg commissions will be overstated!!!")

        raw_costs = self.get_raw_cost_data(instrument_code)

        price = self.get_daily_price(instrument_code)
        positions = self.get_buffered_position(
            instrument_code, roundpositions=roundpositions
        )
        fx = self.get_fx_rate(instrument_code)
        value_of_price_point = self.get_value_of_block_price_move(instrument_code)

        capital = self.get_notional_capital()

        pandl_calculator = pandlCalculationWithCashCostsAndFills(price,
                                                    raw_costs=raw_costs,
                                                       positions=positions,
                                                       capital=capital,
                                                       value_per_point=value_of_price_point,
                                                       delayfill=delayfill,
                                                       fx=fx,
                                                       roundpositions=roundpositions)

        account_curve = accountCurve(pandl_calculator, weighted=True)

        return account_curve
