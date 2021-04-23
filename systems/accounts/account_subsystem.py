from systems.system_cache import diagnostic
from systems.accounts.account_costs import accountCosts
from systems.accounts.pandl_calculators.pandl_SR_cost import pandlCalculationWithSRCosts
from systems.accounts.curves.account_curve import accountCurve

class accountSubsystem(accountCosts):

    @diagnostic(not_pickable=True)
    def pandl_for_subsystem(
        self, instrument_code, delayfill=True, roundpositions=False
    ):
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
        >>>
        >>> system.accounts.pandl_for_subsystem("US10", percentage=True).ann_std()
        0.23422378634127036
        """

        self.log.msg(
            "Calculating pandl for subsystem for instrument %s" %
            instrument_code, instrument_code=instrument_code, )

        use_SR_cost = self.use_SR_costs

        if use_SR_cost:
            pandl = self._pandl_for_subsystem_with_SR_costs(instrument_code,
                                                        delayfill=delayfill,
                                                        roundpositions=roundpositions)
        else:
            pandl = self._pandl_for_subsystem_with_actual_costs(instrument_code,
                                                        delayfill=delayfill,
                                                        roundpositions=roundpositions)

        return pandl

    @diagnostic(not_pickable=True)
    def _pandl_for_subsystem_with_SR_costs(
            self, instrument_code, delayfill=True, roundpositions=False
    ):

        price = self.get_daily_price(instrument_code)
        positions = self.get_subsystem_position(instrument_code)

        fx = self.get_fx_rate(instrument_code)

        value_of_price_point = self.get_value_of_block_price_move(instrument_code)
        daily_returns_volatility = self.get_daily_returns_volatility(
            instrument_code
        )


        SR_cost_per_trade = self.get_SR_cost_per_trade_for_instrument(instrument_code)
        subsystem_turnover = self.subsystem_turnover(instrument_code)
        annualised_SR_cost = SR_cost_per_trade * subsystem_turnover

        capital = self.get_notional_capital()

        pandl_calculator = pandlCalculationWithSRCosts(price,
                                                       SR_cost=annualised_SR_cost,
                                                       positions=positions,
                                                       daily_returns_volatility=daily_returns_volatility,
                                                       capital=capital,
                                                       value_per_point=value_of_price_point,
                                                       delayfill=delayfill,
                                                       fx=fx,
                                                       roundpositions=roundpositions)

        account_curve = accountCurve(pandl_calculator)

        return account_curve

    @diagnostic(not_pickable=True)
    def _pandl_for_subsystem_with_actual_costs(
            self, instrument_code, delayfill=True, roundpositions=False
    ):

        raise NotImplementedError