import numpy as np
import pandas as pd

from syscore.pandas.strategy_functions import turnover
from systems.system_cache import diagnostic

from systems.accounts.account_costs import accountCosts


class accountBufferingSubSystemLevel(accountCosts):
    @diagnostic()
    def subsystem_turnover(self, instrument_code: str) -> float:
        positions = self.get_subsystem_position(instrument_code)

        average_position_for_turnover = self.get_average_position_at_subsystem_level(
            instrument_code
        )

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

        buffer_method = self.config.get_element_or_default("buffer_method", "none")
        if buffer_method == "none":
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
        self.log.debug("Calculating buffered subsystem positions")
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


def apply_buffer(
    optimal_position: pd.Series,
    pos_buffers: pd.DataFrame,
    trade_to_edge: bool = False,
    roundpositions: bool = False,
) -> pd.Series:
    """
    Apply a buffer to a position

    If position is outside the buffer, we either trade to the edge of the
    buffer, or to the optimal

    If we're rounding positions, then we floor and ceiling the buffers.

    :param optimal_position: optimal position
    :type optimal_position: pd.Series

    :param pos_buffers:
    :type pos_buffers: Tx2 pd.dataframe, top_pos and bot_pos

    :param trade_to_edge: Trade to the edge (True) or the optimal (False)
    :type trade_to_edge: bool

    :param roundpositions: Produce rounded positions
    :type roundpositions: bool

    :returns: pd.Series
    """

    pos_buffers = pos_buffers.ffill()
    use_optimal_position = optimal_position.ffill()

    top_pos = pos_buffers.top_pos
    bot_pos = pos_buffers.bot_pos

    if roundpositions:
        use_optimal_position = use_optimal_position.round()
        top_pos = top_pos.round()
        bot_pos = bot_pos.round()

    current_position = use_optimal_position.values[0]
    if np.isnan(current_position):
        current_position = 0.0

    buffered_position_list = [current_position]

    for idx in range(len(optimal_position.index))[1:]:
        current_position = apply_buffer_single_period(
            current_position,
            float(use_optimal_position.values[idx]),
            float(top_pos.values[idx]),
            float(bot_pos.values[idx]),
            trade_to_edge=trade_to_edge,
        )
        buffered_position_list.append(current_position)

    buffered_position = pd.Series(buffered_position_list, index=optimal_position.index)

    return buffered_position


def apply_buffer_single_period(
    last_position, optimal_position, top_pos, bot_pos, trade_to_edge
):
    """
    Apply a buffer to a position, single period

    If position is outside the buffer, we either trade to the edge of the
    buffer, or to the optimal

    :param last_position: last position we had
    :type last_position: float

    :param optimal_position: ideal position
    :type optimal_position: float

    :param top_pos: top of buffer
    :type top_pos: float

    :param bot_pos: bottom of buffer
    :type bot_pos: float

    :param trade_to_edge: Trade to the edge (True) or the optimal (False)
    :type trade_to_edge: bool

    :returns: float
    """

    if np.isnan(top_pos) or np.isnan(bot_pos) or np.isnan(optimal_position):
        return last_position

    if last_position > top_pos:
        if trade_to_edge:
            return top_pos
        else:
            return optimal_position
    elif last_position < bot_pos:
        if trade_to_edge:
            return bot_pos
        else:
            return optimal_position
    else:
        return last_position
