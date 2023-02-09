import pandas as pd
import numpy as np

from syscore.pandas.strategy_functions import turnover
from systems.accounts.accounts_stage import Account
from systems.accounts.curves.account_curve import accountCurve
from systems.accounts.curves.account_curve_group import accountCurveGroup
from systems.accounts.curves.dict_of_account_curves import dictOfAccountCurves
from systems.system_cache import output, dont_cache


class accountForOptimisedStage(Account):
    @output(not_pickable=True)
    def optimised_portfolio(self, delayfill=True):

        self.log.terse("Calculating pandl for portfolio")
        capital = self.get_notional_capital()
        instruments = self.get_instrument_list()
        dict_of_pandl_by_instrument = dict(
            [
                (
                    instrument_code,
                    self.pandl_for_optimised_instrument(
                        instrument_code, delayfill=delayfill
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

    @dont_cache
    def pandl_for_optimised_instrument(
        self, instrument_code: str, delayfill: bool = True
    ) -> accountCurve:

        self.log.msg(
            "Calculating pandl for instrument for %s" % instrument_code,
            instrument_code=instrument_code,
        )

        positions = self.get_optimised_position(instrument_code)

        instrument_pandl = self._pandl_for_instrument_with_positions(
            instrument_code, positions=positions, delayfill=delayfill
        )

        return instrument_pandl

    def total_optimised_portfolio_level_turnover(self) -> float:
        list_of_instruments = self.get_instrument_list()
        list_of_turnovers_at_portfolio_level = [
            self.optimised_turnover_at_portfolio_level(instrument_code)
            for instrument_code in list_of_instruments
        ]

        total_turnover = np.nansum(list_of_turnovers_at_portfolio_level)

        return total_turnover

    def optimised_turnover_at_portfolio_level(
        self,
        instrument_code: str,
    ) -> float:

        ## assumes we use all capital
        average_position_for_turnover = self.get_volatility_scalar(instrument_code)

        ## Using actual capital
        positions = self.get_optimised_position(instrument_code)

        ## Turnover will be at portfolio level, so a small number, but meaningful when added up
        return turnover(positions, average_position_for_turnover)

    def get_optimised_position(self, instrument_code: str) -> pd.Series:
        opt_position_df = self.get_optimised_position_df()
        return opt_position_df[instrument_code]

    def get_optimised_position_df(self) -> pd.DataFrame:
        return self.parent.optimisedPositions.get_optimised_position_df()
