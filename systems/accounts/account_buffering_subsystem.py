import pandas as pd

from syscore.algos import apply_buffer
from syscore.objects import missing_data
from syscore.pdutils import turnover
from systems.system_cache import diagnostic

from systems.accounts.account_costs import accountCosts


class accountBufferingSubSystemLevel(accountCosts):
    @diagnostic()
    def subsystem_turnover(self, instrument_code: str) -> float:
        positions = self.get_subsystem_position(instrument_code)

        average_position_for_turnover = self.get_volatility_scalar(instrument_code)

        subsystem_turnover = turnover(positions, average_position_for_turnover)

        return subsystem_turnover

    @diagnostic()
    def get_buffered_subsystem_position(
        self, instrument_code: str, roundpositions: bool = True
    ) -> pd.Series:
        """
        Get the buffered position

        :param instrument_code: instrument to get

        :param roundpositions: Round positions to whole contracts
        :type roundpositions: bool

        :returns: Tx1 pd.DataFrame

        >>> from systems.basesystem import System
        >>> from systems.tests.testdata import get_test_object_futures_with_portfolios
        >>> (portfolio, posobject, combobject, capobject, rules, rawdata, data, config)=get_test_object_futures_with_portfolios()
        >>> system=System([portfolio, posobject, combobject, capobject, rules, rawdata, Account()], data, config)
        >>>
        >>> system.accounts.get_buffered_position("EDOLLAR").tail(3)
                    position
        2015-12-09         1
        2015-12-10         1
        2015-12-11         1
        """

        optimal_position = self.get_subsystem_position(instrument_code)

        buffer_method = self.config.get_element_or_missing_data("buffer_method")
        if buffer_method is missing_data or buffer_method == "none":
            if roundpositions:
                return optimal_position.round()
            else:
                return optimal_position

        pos_buffers = self.get_buffers_for_subsystem_position(instrument_code)

        buffered_position = (
            self._get_buffered_subsystem_position_given_optimal_position_and_buffers(
                optimal_position=optimal_position,
                pos_buffers=pos_buffers,
                roundpositions=roundpositions,
            )
        )

        return buffered_position

    def _get_buffered_subsystem_position_given_optimal_position_and_buffers(
        self,
        optimal_position: pd.Series,
        pos_buffers: pd.DataFrame,
        roundpositions: bool = True,
    ) -> pd.Series:

        self.log.msg("Calculating buffered subsystem positions")
        trade_to_edge = self.config.buffer_trade_to_edge

        buffered_position = apply_buffer(
            optimal_position,
            pos_buffers,
            trade_to_edge=trade_to_edge,
            roundpositions=roundpositions,
        )

        return buffered_position

    @diagnostic()
    def get_buffers_for_subsystem_position(self, instrument_code: str) -> pd.DataFrame:
        """
        Get the buffered position from a previous module

        :param instrument_code: instrument to get values for
        :type instrument_code: str

        :returns: Tx2 pd.DataFrame: columns top_pos, bot_pos

        KEY INPUT
        """

        return self.parent.positionSize.get_buffers_for_subsystem_position(
            instrument_code
        )
