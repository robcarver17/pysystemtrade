from copy import copy

import pandas as pd

from sysdata.data_blob import dataBlob
from sysdata.arctic.arctic_optimal_positions import arcticOptimalPositionData
from sysdata.production.optimal_positions import optimalPositionData
from sysobjects.production.optimal_positions import (
    listOfOptimalPositionsAcrossInstrumentStrategies,
    baseOptimalPosition,
    listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies,
    instrumentStrategyAndOptimalPosition,
)
from sysobjects.production.tradeable_object import instrumentStrategy
from sysproduction.data.generic_production_data import productionDataLayerGeneric
from sysproduction.data.positions import diagPositions
from sysproduction.data.config import (
    get_list_of_stale_instruments,
    get_list_of_stale_strategies,
)


class dataOptimalPositions(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_object(arcticOptimalPositionData)

        return data

    def get_list_of_current_optimal_positions_for_strategy_name(
        self, strategy_name: str
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:

        all_optimal_positions = self.get_list_of_optimal_positions()
        optimal_positions_for_strategy = all_optimal_positions.filter_by_strategy(
            strategy_name
        )

        return optimal_positions_for_strategy

    def get_list_of_instruments_for_strategy_with_optimal_position(
        self, strategy_name: str, raw_positions=False
    ) -> list:
        if raw_positions:
            use_strategy_name = strategy_name_with_raw_tag(strategy_name)
        else:
            use_strategy_name = strategy_name

        list_of_instruments = self.db_optimal_position_data.get_list_of_instruments_for_strategy_with_optimal_position(
            use_strategy_name
        )

        return list_of_instruments

    def get_list_of_strategies_with_optimal_position(self) -> list:

        list_of_strategies = (
            self.db_optimal_position_data.list_of_strategies_with_optimal_position()
        )
        list_of_strategies = remove_raw_strategies(list_of_strategies)

        return list_of_strategies

    def get_current_optimal_position_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy, raw_positions=False
    ) -> baseOptimalPosition:

        if raw_positions:
            use_instrument_strategy = instrument_strategy_with_raw_tag(
                instrument_strategy
            )
        else:
            use_instrument_strategy = instrument_strategy

        current_optimal_position_entry = self.db_optimal_position_data.get_current_optimal_position_for_instrument_strategy(
            use_instrument_strategy
        )

        return current_optimal_position_entry

    def get_optimal_position_as_df_for_instrument_strategy(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.DataFrame:

        df_object = self.db_optimal_position_data.get_optimal_position_as_df_for_instrument_strategy(
            instrument_strategy
        )

        return df_object

    def update_optimal_position_for_instrument_strategy(
        self,
        instrument_strategy: instrumentStrategy,
        position_entry: baseOptimalPosition,
        raw_positions=False,
    ):
        if raw_positions:
            use_instrument_strategy = instrument_strategy_with_raw_tag(
                instrument_strategy
            )
        else:
            use_instrument_strategy = instrument_strategy

        self.db_optimal_position_data.update_optimal_position_for_instrument_strategy(
            use_instrument_strategy, position_entry
        )

    def get_list_of_optimal_positions(
        self,
    ) -> listOfOptimalPositionsAcrossInstrumentStrategies:

        ## drop stale markets
        list_of_optimal_positions_and_instrument_strategies = (
            self.db_optimal_position_data.get_list_of_optimal_positions()
        )

        list_of_optimal_positions_and_instrument_strategies = (
            remove_raw_from_list_of_optimal_positions_and_instrument_strategies(
                list_of_optimal_positions_and_instrument_strategies
            )
        )

        list_of_optimal_positions_and_instrument_strategies = remove_stale_strategies_and_instruments_from_list_of_optimal_positions_and_instrument_strategies(
            list_of_optimal_positions_and_instrument_strategies=list_of_optimal_positions_and_instrument_strategies,
            data=self.data,
        )

        return list_of_optimal_positions_and_instrument_strategies

    def get_pd_of_position_breaks(self) -> pd.DataFrame:
        optimal_and_current = self.get_list_of_optimal_and_current_positions()
        optimal_and_current_as_pd = optimal_and_current.as_pd_with_breaks()

        return optimal_and_current_as_pd

    def get_list_of_optimal_position_breaks(self) -> list:
        opt_positions = self.get_pd_of_position_breaks()
        with_breaks = opt_positions[opt_positions.breaks]
        items_with_breaks = list(with_breaks.index)

        return items_with_breaks

    def get_list_of_optimal_and_current_positions(
        self,
    ) -> listOfOptimalAndCurrentPositionsAcrossInstrumentStrategies:

        optimal_positions = self.get_list_of_optimal_positions()

        position_data = diagPositions(self.data)
        current_positions = (
            position_data.get_all_current_strategy_instrument_positions()
        )
        optimal_and_current = optimal_positions.add_positions(current_positions)

        return optimal_and_current

    @property
    def db_optimal_position_data(self) -> optimalPositionData:
        return self.data.db_optimal_position


POST_TAG_FOR_RAW_OPTIMAL_POSITION = "_raw"


def remove_raw_strategies(list_of_strategies: list) -> list:
    list_of_strategies = [
        strategy_name
        for strategy_name in list_of_strategies
        if is_not_raw_strategy(strategy_name)
    ]

    return list_of_strategies


def is_not_raw_strategy(strategy_name: str) -> bool:
    return not is_raw_strategy(strategy_name)


def is_raw_strategy(strategy_name: str) -> bool:
    return strategy_name.endswith(POST_TAG_FOR_RAW_OPTIMAL_POSITION)


def remove_raw_from_list_of_optimal_positions_and_instrument_strategies(
    list_of_optimal_positions_and_instrument_strategies: listOfOptimalPositionsAcrossInstrumentStrategies,
) -> listOfOptimalPositionsAcrossInstrumentStrategies:

    list_of_optimal_positions_and_instrument_strategies = [
        optimal_position_and_instrument_strategy
        for optimal_position_and_instrument_strategy in list_of_optimal_positions_and_instrument_strategies
        if is_not_raw_optimal_position_and_instrument_strategy(
            optimal_position_and_instrument_strategy
        )
    ]

    return listOfOptimalPositionsAcrossInstrumentStrategies(
        list_of_optimal_positions_and_instrument_strategies
    )


def is_not_raw_optimal_position_and_instrument_strategy(
    optimal_position_and_instrument_strategy: instrumentStrategyAndOptimalPosition,
) -> bool:

    return is_not_raw_instrument_strategy(
        optimal_position_and_instrument_strategy.instrument_strategy
    )


def is_not_raw_instrument_strategy(instrument_strategy: instrumentStrategy) -> bool:
    return is_not_raw_strategy(instrument_strategy.strategy_name)


def instrument_strategy_with_raw_tag(
    instrument_strategy: instrumentStrategy,
) -> instrumentStrategy:
    original_strategy_name = copy(instrument_strategy.strategy_name)
    strategy_name = strategy_name_with_raw_tag(original_strategy_name)

    new_instrument_strategy = instrumentStrategy(
        strategy_name=strategy_name, instrument_code=instrument_strategy.instrument_code
    )

    return new_instrument_strategy


def strategy_name_with_raw_tag(strategy_name: str) -> str:
    return strategy_name + POST_TAG_FOR_RAW_OPTIMAL_POSITION


def remove_stale_strategies_and_instruments_from_list_of_optimal_positions_and_instrument_strategies(
    list_of_optimal_positions_and_instrument_strategies: listOfOptimalPositionsAcrossInstrumentStrategies,
) -> listOfOptimalPositionsAcrossInstrumentStrategies:

    filtered_list = remove_stale_strategies_from_list_of_optimal_positions_and_instrument_strategies(
        list_of_optimal_positions_and_instrument_strategies=list_of_optimal_positions_and_instrument_strategies,
    )

    twice_filtered_list = remove_stale_instruments_from_list_of_optimal_positions_and_instrument_strategies(
        list_of_optimal_positions_and_instrument_strategies=filtered_list
    )

    return twice_filtered_list


def remove_stale_strategies_from_list_of_optimal_positions_and_instrument_strategies(
    list_of_optimal_positions_and_instrument_strategies: listOfOptimalPositionsAcrossInstrumentStrategies,
) -> listOfOptimalPositionsAcrossInstrumentStrategies:

    list_of_stale_strategies = get_list_of_stale_strategies()
    new_list = (
        list_of_optimal_positions_and_instrument_strategies.filter_removing_strategies(
            list_of_stale_strategies
        )
    )

    return new_list


def remove_stale_instruments_from_list_of_optimal_positions_and_instrument_strategies(
    list_of_optimal_positions_and_instrument_strategies: listOfOptimalPositionsAcrossInstrumentStrategies,
) -> listOfOptimalPositionsAcrossInstrumentStrategies:

    list_of_stale_instruments = get_list_of_stale_instruments()
    new_list = (
        list_of_optimal_positions_and_instrument_strategies.filter_removing_instruments(
            list_of_stale_instruments
        )
    )

    return new_list
