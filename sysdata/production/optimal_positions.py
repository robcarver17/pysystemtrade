"""

Optimal positions describe what a particular trading strategy would like to do, conditional (or not) on prices and
  current positions

The exact implementation of this depends on the strategy.
A basic class is an optimal position with buffers around it.
A mean reversion style class would include price buffers

"""

from syscore.objects import failure
from sysdata.production.timed_storage import (
    listOfEntriesData,
)
from sysobjects.production.optimal_positions import simpleOptimalPosition, bufferedOptimalPositions, \
    instrumentStrategyAndOptimalPosition, listOfOptimalPositionsAcrossInstrumentStrategies
from sysobjects.production.timed_storage import listOfEntries
from sysobjects.production.strategy import instrumentStrategy


## THIS HAS TO STAY HERE OR OLD DATA WILL BREAK - DO NOT MOVE
class simpleOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return simpleOptimalPosition


## THIS HAS TO STAY HERE OR OLD DATA WILL BREAK - DO NOT MOVE
class bufferedOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions over time
    """

    def _entry_class(self):
        return bufferedOptimalPositions

STRATEGY_KEY = 'strategy_name'
INSTRUMENT_KEY = 'instrument_code'

class optimalPositionData(listOfEntriesData):
    """
    Store and retrieve the optimal positions assigned to a particular strategy

    We store the type of list in the data
    """

    def _data_class_name(self):
        # This is the default, may be overriden
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def get_list_of_optimal_positions_for_strategy(self, strategy_name: str):
        list_of_instrument_codes = (
            self.get_list_of_instruments_for_strategy_with_optimal_position(
                strategy_name
            )
        )
        list_of_optimal_positions_and_instrument_strategies = [
            #FIXME WORK ON STRATS DIRECTLY
            self.get_instrument_strategy_and_optimal_position(instrumentStrategy(strategy_name=strategy_name,
                                                                                 instrument_code=instrument_code))
            for instrument_code in list_of_instrument_codes
        ]
        output = listOfOptimalPositionsAcrossInstrumentStrategies(
            list_of_optimal_positions_and_instrument_strategies
        )

        return output

    def get_list_of_optimal_positions(self):
        list_of_strategies_and_instruments = (
            self.get_list_of_strategies_and_instruments_with_optimal_position()
        )
        list_of_optimal_positions_and_tradeable_objects = [
            self.get_instrument_strategy_and_optimal_position(
                #FIXME
                instrumentStrategy(instrument_code=instrument_code, strategy_name=strategy_name)
            )
            for strategy_name, instrument_code in list_of_strategies_and_instruments
        ]
        output = listOfOptimalPositionsAcrossInstrumentStrategies(
            list_of_optimal_positions_and_tradeable_objects
        )

        return output


    def get_instrument_strategy_and_optimal_position(
            self, instrument_strategy: instrumentStrategy)\
            -> instrumentStrategyAndOptimalPosition:
        
        optimal_position = (
            self.get_current_optimal_position_for_instrument_strategy(
                instrument_strategy
            )
        )
        instrument_strategy_and_optimal_position = instrumentStrategyAndOptimalPosition(
            instrument_strategy, optimal_position)

        return instrument_strategy_and_optimal_position

    def get_optimal_position_as_df_for_strategy_and_instrument_code(
        self, strategy_name, instrument_code
    ):
        #FIXME REMOVE
        df_object = self.get_optimal_position_as_df_for_instrument_strategy(instrumentStrategy(instrument_code=instrument_code, strategy_name=strategy_name))
        return df_object


    def get_optimal_position_as_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):
        position_series = self._get_series_for_args_dict(
            instrument_strategy.as_dict()
        )
        df_object = position_series.as_pd_df()
        return df_object


    def get_current_optimal_position_for_instrument_strategy(
            self, strategy_instrument: instrumentStrategy
    ):
        current_optimal_position_entry = self._get_current_entry_for_args_dict(
            strategy_instrument.as_dict()
        )

        return current_optimal_position_entry

    def update_optimal_position_for_strategy_and_instrument(
        self, strategy_name, instrument_code, position_entry
    ):
        ## FIXME
        self.update_optimal_position_for_strategy_and_instrument(instrumentStrategy(strategy_name=strategy_name, instrument_code=instrument_code))

    def update_optimal_position_for_instrument_strategy(self,
                                                        instrument_strategy: instrumentStrategy,
                                                        position_entry: simpleOptimalPosition):
        try:
            self._update_entry_for_args_dict(
                position_entry,
                instrument_strategy.as_dict(),
            )
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s with %s"
                % (str(e), str(instrument_strategy), str(position_entry))
            )
            return failure

    def get_list_of_strategies_and_instruments_with_optimal_position(self):
        #FIXME RETURN INSTRUMENT_STRATEGY
        list_of_args_dict = self._get_list_of_args_dict()
        strat_instr_tuples = []
        for arg_entry in list_of_args_dict:
            strat_instr_tuples.append(
                (arg_entry["strategy_name"], arg_entry["instrument_code"])
            )

        return strat_instr_tuples

    def get_list_of_instruments_for_strategy_with_optimal_position(
            self, strategy_name):
        # FIXME RETURN INSTRUMENT_STRATEGY USE FILTER
        list_of_all_positions = (
            self.get_list_of_strategies_and_instruments_with_optimal_position()
        )
        list_of_instruments = [
            position[1]
            for position in list_of_all_positions
            if position[0] == strategy_name
        ]

        return list_of_instruments

