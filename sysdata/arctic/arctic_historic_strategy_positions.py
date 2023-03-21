import datetime
import pandas as pd

from sysobjects.production.tradeable_object import (
    listOfInstrumentStrategies,
    instrumentStrategy,
)
from sysdata.arctic.arctic_connection import arcticData
from sysdata.production.historic_strategy_positions import strategyPositionData
from syscore.exceptions import missingData

from syslogdiag.log_to_screen import logtoscreen

STRATEGY_POSITION_COLLECTION = "strategy_positions"


class arcticStrategyPositionData(strategyPositionData):
    def __init__(self, mongo_db=None, log=logtoscreen("arcticStrategyPositionData")):

        super().__init__(log=log)

        self._arctic = arcticData(STRATEGY_POSITION_COLLECTION, mongo_db=mongo_db)

    def __repr__(self):
        return repr(self._arctic)

    @property
    def arctic(self):
        return self._arctic

    def get_list_of_instrument_strategies(self) -> listOfInstrumentStrategies:
        list_of_keys = self.arctic.get_keynames()
        list_of_instrument_strategies = [
            instrumentStrategy.from_key(key) for key in list_of_keys
        ]

        return listOfInstrumentStrategies(list_of_instrument_strategies)

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
            self.log.warn(
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

        updated_series = current_series.append(new_position_series)
        self._write_updated_position_series_for_instrument_strategy_object(
            instrument_strategy=instrument_strategy, updated_series=updated_series
        )

    def _write_updated_position_series_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy, updated_series: pd.Series
    ):

        ident = instrument_strategy.key
        updated_data_as_df = pd.DataFrame(updated_series)
        updated_data_as_df.columns = ["position"]

        self.arctic.write(ident=ident, data=updated_data_as_df)

    def _delete_position_series_for_instrument_strategy_object_without_checking(
        self, instrument_strategy: instrumentStrategy
    ):
        ident = instrument_strategy.key
        self.arctic.delete(ident)

    def get_position_as_series_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.Series:

        keyname = instrument_strategy.key
        try:
            pd_df = self.arctic.read(keyname)
        except:
            raise missingData

        return pd_df.iloc[:, 0]
