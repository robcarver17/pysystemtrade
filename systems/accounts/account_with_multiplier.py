from copy import copy

import pandas as pd

from syscore.objects import resolve_function
from syscore.pandas.pdutils import from_scalar_values_to_ts

from systems.system_cache import output, diagnostic
from systems.accounts.account_portfolio import accountPortfolio
from systems.accounts.account_buffering_system import accountBufferingSystemLevel

from systems.accounts.curves.dict_of_account_curves import dictOfAccountCurves
from systems.accounts.curves.account_curve_group import accountCurveGroup
from systems.accounts.curves.account_curve import accountCurve


class accountWithMultiplier(accountPortfolio, accountBufferingSystemLevel):
    @output(not_pickable=True)
    def portfolio_with_multiplier(self, delayfill=True, roundpositions=True):

        self.log.terse("Calculating pandl for portfolio with multiplier")
        capital = self.get_actual_capital()
        instruments = self.get_instrument_list()
        port_pandl = [
            (
                instrument_code,
                self.pandl_for_instrument_with_multiplier(
                    instrument_code, delayfill=delayfill, roundpositions=roundpositions
                ),
            )
            for instrument_code in instruments
        ]

        port_pandl = dictOfAccountCurves(port_pandl)

        port_pandl = accountCurveGroup(port_pandl, capital=capital, weighted=True)

        return port_pandl

    @output(not_pickable=True)
    def pandl_for_instrument_with_multiplier(
        self, instrument_code: str, delayfill=True, roundpositions=True
    ) -> accountCurve:
        """
        Get the p&l for one instrument, using variable capital

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: accountCurve

        """

        self.log.msg(
            "Calculating pandl for instrument for %s with capital multiplier"
            % instrument_code,
            instrument_code=instrument_code,
        )

        positions = self.get_buffered_position_with_multiplier(
            instrument_code, roundpositions=roundpositions
        )

        instrument_pandl = self._pandl_for_instrument_with_positions(
            instrument_code,
            positions=positions,
            delayfill=delayfill,
            roundpositions=roundpositions,
        )

        return instrument_pandl

    @diagnostic()
    def get_buffered_position_with_multiplier(
        self, instrument_code: str, roundpositions: bool = True
    ) -> pd.Series:
        """
        Get the buffered position

        :param instrument_code: instrument to get

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: Tx1 pd.DataFrame

        """

        optimal_position = self.get_actual_position(instrument_code)
        pos_buffers = self.get_actual_buffers_for_position(instrument_code)

        buffered_position = (
            self._get_buffered_position_given_optimal_position_and_buffers(
                optimal_position=optimal_position,
                pos_buffers=pos_buffers,
                roundpositions=roundpositions,
            )
        )

        return buffered_position

    @diagnostic()
    def get_actual_capital(self) -> pd.Series:
        """
        Get a capital multiplier multiplied by notional capital

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: pd.Series

        """

        capmult = self.capital_multiplier()
        notional = self.get_notional_capital()

        if type(notional) is int or type(notional) is float:
            notional_ts = from_scalar_values_to_ts(notional, capmult.index)
        else:
            notional_ts = notional.reindex(capmult.index).ffill()

        capital = capmult * notional_ts

        return capital

    @diagnostic()
    def capital_multiplier(self) -> pd.Series:
        """
        Get a capital multiplier

        :param delayfill: Lag fills by one day
        :type delayfill: bool

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: pd.Series

        """
        config = self.config
        system = self.parent

        capmult_params = copy(config.capital_multiplier)
        capmult_func = resolve_function(capmult_params.pop("func"))

        capmult = capmult_func(system, **capmult_params)

        capmult = capmult.reindex(self.portfolio().index).ffill()

        return capmult
