"""

Optimal positions describe what a particular trading strategy would like to do, conditional (or not) on prices and
  current positions

The exact implementation of this depends on the strategy.
A basic class is an optimal position with buffers around it.
A mean reversion style class would include price buffers

"""

import pandas as pd

from syscore.objects import arg_not_supplied, failure, success, missing_data
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.production.generic_timed_storage import (
    timedEntry,
    listOfEntries,
    listOfEntriesData,
)
from sysdata.production.current_positions import (
    instrumentStrategy,
    instrumentStrategyPosition,
)


class simpleOptimalPosition(timedEntry):
    """
    This is the simplest possible optimal positions object

    """

    def _setup_args_data(self):
        self._star_args = ["position"]  # compulsory args

    def _name_(self):
        return "simpleOptimalPosition"

    def _containing_data_class_name(self):
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def check_position_break(self, position):
        return self.position == position


class bufferedOptimalPositions(timedEntry):
    """
    Here is one with buffers

    """

    def _setup_args_data(self):
        self._star_args = [
            "lower_position",
            "upper_position",
            "reference_price",
            "reference_contract",
        ]  # compulsory args

    def _name_(self):
        return "bufferedOptimalPosition"

    def _containing_data_class_name(self):
        return (
            "sysdata.production.optimal_positions.bufferedOptimalPositionForInstrument"
        )

    def _kwargs_checks(self, kwargs):
        try:
            assert kwargs["upper_position"] >= kwargs["lower_position"]
        except BaseException:
            raise Exception(
                "Upper position has to be higher than lower position")

    def check_position_break(self, position):
        return position < round(self.lower_position) or position > round(
            self.upper_position
        )

    def __repr__(self):
        return "%.3f/%.3f" % (self.lower_position, self.upper_position)


class simpleOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return simpleOptimalPosition


class bufferedOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions over time
    """

    def _entry_class(self):
        return bufferedOptimalPositions


class tradeableObjectAndOptimalPosition(object):
    def __init__(self, tradeable_object, optimal_position_object):
        self.tradeable_object = tradeable_object
        self.optimal_position = optimal_position_object

    def check_tradeable_objects_match(self, tradeable_object_and_position):
        return self.tradeable_object == tradeable_object_and_position.tradeable_object


class tradeableObjectAndOptimalAndCurrentPosition(object):
    def __init__(
            self,
            tradeable_object_and_optimal_position,
            tradeable_object_and_position):
        # this is contains a instrumentStrategyPosition type thing, and a tradeableObjectAndOptimalPosition
        # type thing

        # same tradeable object, so that is stored plus Position, and
        # OptimalPosition
        assert (
            tradeable_object_and_optimal_position.check_tradeable_objects_match(
                tradeable_object_and_position
            )
            is True
        )
        self.tradeable_object = tradeable_object_and_optimal_position.tradeable_object
        self.position = tradeable_object_and_position.position
        self.optimal_position = tradeable_object_and_optimal_position.optimal_position

    def check_break(self):
        return self.optimal_position.check_position_break(self.position)


class listOfOptimalPositionsAcrossTradeableObjects(list):
    # list of tradeableObjectAndOptimalPosition
    # need to set up so sysproduction.positions.optimal position data reports this eg
    # optimal_position_data.get_current_optimal_positions_across_strategies_and_instruments()
    def as_pd(self):
        list_of_keys = [pos.tradeable_object for pos in self]
        list_of_optimal = [pos.optimal_position for pos in self]

        return pd.DataFrame(dict(key=list_of_keys, optimal=list_of_optimal))

    def add_positions(self, position_list):
        # returns listOfBufferedAndCurrentPositionsAcrossTradeableObjects
        # takes as input
        # diag_positions.get_all_current_strategy_instrument_positions() type
        # thing
        list_of_optimal_and_current = []
        list_of_tradeable_objects_position_list = [
            pos.tradeable_object for pos in position_list
        ]
        for opt_pos_object in self:
            tradeable_object = opt_pos_object.tradeable_object
            try:
                idx = list_of_tradeable_objects_position_list.index(
                    tradeable_object)
                relevant_position_item = position_list[idx]
            except ValueError:
                strategy_name = tradeable_object.strategy_name
                instrument_code = tradeable_object.instrument_code
                relevant_position_item = instrumentStrategyPosition(
                    0, strategy_name, instrument_code
                )

            new_object = tradeableObjectAndOptimalAndCurrentPosition(
                opt_pos_object, relevant_position_item
            )
            list_of_optimal_and_current.append(new_object)

        list_of_optimal_and_current = (
            listOfOptimalAndCurrentPositionsAcrossTradeableObjects(
                list_of_optimal_and_current
            )
        )
        return list_of_optimal_and_current


class listOfOptimalAndCurrentPositionsAcrossTradeableObjects(list):
    # list of tradeableObjectAndOptimalAndCurrentPosition
    #
    # needs to be gettable by sysproduction.data.diagPositions

    def check_breaks(self):
        # return a list of bool
        list_of_breaks = [pos.check_break() for pos in self]

        return list_of_breaks

    def as_pd_with_breaks(self):
        tradeable_objects = [pos.tradeable_object for pos in self]
        optimal_positions = [pos.optimal_position for pos in self]
        current_positions = [pos.position for pos in self]
        breaks = self.check_breaks()

        ans = pd.DataFrame(
            dict(
                current=current_positions,
                optimal=optimal_positions,
                breaks=breaks),
            index=tradeable_objects,
        )

        return ans


class optimalPositionData(listOfEntriesData):
    """
    Store and retrieve the optimal positions assigned to a particular strategy

    We store the type of list in the data
    """

    def _name(self):
        return "optimalPositionData"

    def _data_class_name(self):
        # This is the default, may be overriden
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def get_list_of_optimal_positions_for_strategy(self, strategy_name):
        list_of_instrument_codes = (
            self.get_list_of_instruments_for_strategy_with_optimal_position(
                strategy_name
            )
        )
        list_of_optimal_positions_and_tradeable_objects = [
            self.get_tradeable_object_and_optimal_position(
                strategy_name, instrument_code
            )
            for instrument_code in list_of_instrument_codes
        ]
        output = listOfOptimalPositionsAcrossTradeableObjects(
            list_of_optimal_positions_and_tradeable_objects
        )

        return output

    def get_list_of_optimal_positions(self):
        list_of_strategies_and_instruments = (
            self.get_list_of_strategies_and_instruments_with_optimal_position()
        )
        list_of_optimal_positions_and_tradeable_objects = [
            self.get_tradeable_object_and_optimal_position(
                strategy_name, instrument_code
            )
            for strategy_name, instrument_code in list_of_strategies_and_instruments
        ]
        output = listOfOptimalPositionsAcrossTradeableObjects(
            list_of_optimal_positions_and_tradeable_objects
        )

        return output

    def get_tradeable_object_and_optimal_position(
            self, strategy_name, instrument_code):
        optimal_position = (
            self.get_current_optimal_position_for_strategy_and_instrument(
                strategy_name, instrument_code
            )
        )
        tradeable_object = instrumentStrategy(strategy_name, instrument_code)
        tradeable_object_and_optimal_position = tradeableObjectAndOptimalPosition(
            tradeable_object, optimal_position)

        return tradeable_object_and_optimal_position

    def get_optimal_position_as_df_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        position_series = self._get_series_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code)
        )
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_optimal_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        current_optimal_position_entry = self._get_current_entry_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code)
        )

        return current_optimal_position_entry

    def update_optimal_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, position_entry
    ):

        try:
            self._update_entry_for_args_dict(
                position_entry,
                dict(
                    strategy_name=strategy_name,
                    instrument_code=instrument_code),
            )
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s/%s with %s"
                % (str(e), strategy_name, instrument_code, str(position_entry))
            )
            return failure

    def get_list_of_strategies_and_instruments_with_optimal_position(self):
        list_of_args_dict = self._get_list_of_args_dict()
        strat_instr_tuples = []
        for arg_entry in list_of_args_dict:
            strat_instr_tuples.append(
                (arg_entry["strategy_name"], arg_entry["instrument_code"])
            )

        return strat_instr_tuples

    def get_list_of_instruments_for_strategy_with_optimal_position(
            self, strategy_name):
        list_of_all_positions = (
            self.get_list_of_strategies_and_instruments_with_optimal_position()
        )
        list_of_instruments = [
            position[1]
            for position in list_of_all_positions
            if position[0] == strategy_name
        ]

        return list_of_instruments

    def delete_last_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, are_you_sure=False
    ):
        self._delete_last_entry_for_args_dict(
            dict(strategy_name=strategy_name, instrument_code=instrument_code),
            are_you_sure=are_you_sure,
        )
