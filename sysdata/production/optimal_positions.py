"""

Optimal positions describe what a particular trading strategy would like to do, conditional (or not) on prices and
  current positions

The exact implementation of this depends on the strategy.
A basic class is an optimal position with buffers around it.
A mean reversion style class would include price buffers

"""

from syscore.constants import failure
from sysdata.production.timed_storage import (
    listOfEntriesData,
)
from sysobjects.production.optimal_positions import (
    simpleOptimalPosition,
    bufferedOptimalPositions,
    instrumentStrategyAndOptimalPosition,
    listOfOptimalPositionsAcrossInstrumentStrategies,
    optimalPositionWithReference,
    optimalPositionWithDynamicCalculations,
)
from sysobjects.production.timed_storage import listOfEntries
from sysobjects.production.tradeable_object import (
    listOfInstrumentStrategies,
    instrumentStrategy,
)


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


class dynamicOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions over time
    """

    def _entry_class(self):
        return optimalPositionWithDynamicCalculations


## THIS HAS TO STAY HERE OR OLD DATA WILL BREAK - DO NOT MOVE
class optimalPositionWithReferenceForAsset(listOfEntries):
    """
    A list of positions over time
    """

    def _entry_class(self):
        return optimalPositionWithReference


class optimalPositionData(listOfEntriesData):
    """
    Store and retrieve the optimal positions assigned to a particular strategy

    We store the type of list in the data
    """

    def _data_class_name(self):
        # This is the default, may be overriden
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def get_list_of_optimal_positions_for_strategy(
        self, strategy_name: str
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:
        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_for_strategy_with_optimal_position(
                strategy_name
            )
        )

        list_of_instrument_strategies_with_positions = (
            self.get_list_of_optimal_positions_given_list_of_instrument_strategies(
                list_of_instrument_strategies
            )
        )

        return list_of_instrument_strategies_with_positions

    def get_list_of_optimal_positions(
        self,
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:
        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_with_optimal_position()
        )

        list_of_optimal_positions_and_instrument_strategies = (
            self.get_list_of_optimal_positions_given_list_of_instrument_strategies(
                list_of_instrument_strategies
            )
        )

        return list_of_optimal_positions_and_instrument_strategies

    def get_list_of_optimal_positions_given_list_of_instrument_strategies(
        self, list_of_instrument_strategies: listOfInstrumentStrategies
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:

        list_of_optimal_positions_and_instrument_strategies = [
            self.get_instrument_strategy_and_optimal_position(instrument_strategy)
            for instrument_strategy in list_of_instrument_strategies
        ]

        list_of_optimal_positions_and_instrument_strategies = (
            listOfOptimalPositionsAcrossInstrumentStrategies(
                list_of_optimal_positions_and_instrument_strategies
            )
        )

        return list_of_optimal_positions_and_instrument_strategies

    def get_instrument_strategy_and_optimal_position(
        self, instrument_strategy: instrumentStrategy
    ) -> instrumentStrategyAndOptimalPosition:

        optimal_position = self.get_current_optimal_position_for_instrument_strategy(
            instrument_strategy
        )
        instrument_strategy_and_optimal_position = instrumentStrategyAndOptimalPosition(
            instrument_strategy, optimal_position
        )

        return instrument_strategy_and_optimal_position

    def get_optimal_position_as_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):
        position_series = self._get_series_for_args_dict(instrument_strategy.as_dict())
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_optimal_position_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ):
        current_optimal_position_entry = self._get_current_entry_for_args_dict(
            instrument_strategy.as_dict()
        )

        return current_optimal_position_entry

    def update_optimal_position_for_instrument_strategy(
        self,
        instrument_strategy: instrumentStrategy,
        position_entry: simpleOptimalPosition,
    ):
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

    def get_list_of_instruments_for_strategy_with_optimal_position(
        self, strategy_name: str
    ) -> list:

        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_with_optimal_position()
        )

        list_of_instruments = (
            list_of_instrument_strategies.get_list_of_instruments_for_strategy(
                strategy_name
            )
        )

        return list_of_instruments

    def list_of_strategies_with_optimal_position(self) -> list:
        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_with_optimal_position()
        )

        list_of_strategies = list_of_instrument_strategies.get_list_of_strategies()

        return list_of_strategies

    def get_list_of_instrument_strategies_for_strategy_with_optimal_position(
        self, strategy_name: str
    ) -> listOfInstrumentStrategies:

        list_of_instrument_strategies = (
            self.get_list_of_instrument_strategies_with_optimal_position()
        )
        list_of_instrument_strategies_for_strategy = list_of_instrument_strategies.get_list_of_instrument_strategies_for_strategy(
            strategy_name
        )

        return list_of_instrument_strategies_for_strategy

    def get_list_of_instrument_strategies_with_optimal_position(
        self,
    ) -> listOfInstrumentStrategies:

        list_of_args_dict = self._get_list_of_args_dict()
        list_of_instrument_strategies = []
        for arg_entry in list_of_args_dict:
            list_of_instrument_strategies.append(
                instrumentStrategy.from_dict(arg_entry)
            )
        list_of_instrument_strategies = listOfInstrumentStrategies(
            list_of_instrument_strategies
        )

        return list_of_instrument_strategies
