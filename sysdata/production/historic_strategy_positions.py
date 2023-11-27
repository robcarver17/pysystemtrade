from sysdata.base_data import baseData

import pandas as pd

from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied

from sysobjects.production.positions import (
    instrumentStrategyPosition,
    listOfInstrumentStrategyPositions,
)
from sysobjects.production.tradeable_object import (
    listOfInstrumentStrategies,
    instrumentStrategy,
)
import datetime


class strategyPositionData(baseData):
    """
    Store and retrieve the instrument positions assigned to a particular strategy

    We store the type of list in the data
    """

    def __repr__(self):
        return "straegyPositionData object"

    def get_current_position_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
    ) -> int:
        try:
            position_series = (
                self.get_position_as_series_for_instrument_strategy_object(
                    instrument_strategy
                )
            )
        except missingData:
            return 0

        if len(position_series) == 0:
            return 0

        return position_series.iloc[-1]

    def update_position_for_instrument_strategy_object(
        self,
        instrument_strategy: instrumentStrategy,
        position: int,
        date: datetime.datetime = arg_not_supplied,
    ):
        if date is arg_not_supplied:
            date = datetime.datetime.now()

        try:
            self._update_position_for_instrument_strategy_object_with_date(
                instrument_strategy=instrument_strategy,
                position=position,
                date_index=date,
            )
        except Exception as e:
            self.log.critical(
                "Error %s when updating position for %s with %s"
                % (str(e), str(instrument_strategy), str(position))
            )

    def get_list_of_strategies_and_instruments_with_positions(
        self, ignore_zero_positions: bool = True
    ) -> listOfInstrumentStrategies:
        list_of_instrument_strategies = self.get_list_of_instrument_strategies()

        if ignore_zero_positions:
            list_of_instrument_strategies = [
                instrument_strategy
                for instrument_strategy in list_of_instrument_strategies
                if self.get_current_position_for_instrument_strategy_object(
                    instrument_strategy
                )
                != 0
            ]

            list_of_instrument_strategies = listOfInstrumentStrategies(
                list_of_instrument_strategies
            )

        return list_of_instrument_strategies

    def get_list_of_instruments_for_strategy_with_position(
        self, strategy_name, ignore_zero_positions=True
    ) -> list:
        list_of_instrument_strategies = (
            self.get_list_of_strategies_and_instruments_with_positions(
                ignore_zero_positions=ignore_zero_positions
            )
        )
        list_of_instruments = (
            list_of_instrument_strategies.get_list_of_instruments_for_strategy(
                strategy_name
            )
        )

        return list_of_instruments

    def get_list_of_strategies_with_positions(self) -> list:
        list_of_instrument_strategies = (
            self.get_list_of_strategies_and_instruments_with_positions(
                ignore_zero_positions=True
            )
        )
        list_of_strategies = list_of_instrument_strategies.get_list_of_strategies()

        return list_of_strategies

    def delete_last_position_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy, are_you_sure: bool = False
    ):
        if are_you_sure:
            self._delete_last_position_for_instrument_strategy_object_without_checking(
                instrument_strategy=instrument_strategy
            )
        else:
            self.log.warning("Have to be sure to delete last position")

    def get_all_current_positions_as_df(self) -> pd.DataFrame:
        return (
            self.get_all_current_positions_as_list_with_instrument_objects().as_pd_df()
        )

    def get_all_current_positions_as_list_with_instrument_objects(
        self,
    ) -> listOfInstrumentStrategyPositions:
        """
        Current positions are returned in a different class

        :return: listOfInstrumentStrategyPositions
        """

        list_of_instrument_strategies = self.get_list_of_instrument_strategies()
        current_positions = []
        for instrument_strategy in list_of_instrument_strategies:
            position = self.get_current_position_for_instrument_strategy_object(
                instrument_strategy
            )
            if position == 0:
                continue
            position_object = instrumentStrategyPosition(position, instrument_strategy)
            current_positions.append(position_object)

        list_of_current_position_objects = listOfInstrumentStrategyPositions(
            current_positions
        )

        return list_of_current_position_objects

    def _delete_last_position_for_instrument_strategy_object_without_checking(
        self, instrument_strategy: instrumentStrategy
    ):
        try:
            current_series = self.get_position_as_series_for_instrument_strategy_object(
                instrument_strategy
            )
            self._delete_last_position_for_instrument_strategy_object_without_checking_with_current_data(
                instrument_strategy=instrument_strategy, current_series=current_series
            )
        except missingData:
            ## no existing data can't delete
            self.log.warning(
                "Can't delete last position for %s, as none present"
                % str(instrument_strategy)
            )

    def _delete_last_position_for_instrument_strategy_object_without_checking_with_current_data(
        self, instrument_strategy: instrumentStrategy, current_series: pd.Series
    ):
        updated_series = current_series.drop(current_series.index[-1])
        if len(updated_series) == 0:
            self._delete_position_series_for_instrument_strategy_object_without_checking(
                instrument_strategy
            )
        else:
            self._write_updated_position_series_for_instrument_strategy_object(
                instrument_strategy=instrument_strategy,
                updated_series=updated_series,
            )

    def _update_position_for_instrument_strategy_object_with_date(
        self,
        instrument_strategy: instrumentStrategy,
        position: int,
        date_index: datetime.datetime,
    ):
        new_position_series = pd.Series([position], index=[date_index])

        try:
            current_series = self.get_position_as_series_for_instrument_strategy_object(
                instrument_strategy
            )
            self._update_position_for_instrument_strategy_object_with_date_and_existing_data(
                instrument_strategy=instrument_strategy,
                current_series=current_series,
                new_position_series=new_position_series,
            )
        except missingData:
            ## no existing data
            ## no need to update, just write the new series
            self._write_updated_position_series_for_instrument_strategy_object(
                instrument_strategy=instrument_strategy,
                updated_series=new_position_series,
            )

    def _update_position_for_instrument_strategy_object_with_date_and_existing_data(
        self,
        instrument_strategy: instrumentStrategy,
        current_series: pd.Series,
        new_position_series: pd.Series,
    ):
        try:
            assert new_position_series.index[0] > current_series.index[-1]
        except:
            error_msg = "Adding a position which is older than the last position!"
            self.log.critical(error_msg)
            raise Exception(error_msg)

        updated_series = current_series._append(new_position_series)
        self._write_updated_position_series_for_instrument_strategy_object(
            instrument_strategy=instrument_strategy, updated_series=updated_series
        )

    def overwrite_position_series_for_instrument_strategy_without_checking(
        self, instrument_strategy: instrumentStrategy, updated_series: pd.Series
    ):
        self._write_updated_position_series_for_instrument_strategy_object(
            instrument_strategy=instrument_strategy, updated_series=updated_series
        )

    def _write_updated_position_series_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy, updated_series: pd.Series
    ):
        raise NotImplementedError

    def _delete_position_series_for_instrument_strategy_object_without_checking(
        self, instrument_strategy: instrumentStrategy
    ):
        raise NotImplementedError

    def get_list_of_instrument_strategies(self) -> listOfInstrumentStrategies:
        raise NotImplementedError

    def get_position_as_series_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.Series:
        raise NotImplementedError
