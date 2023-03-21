import pandas as pd
from sysdata.arctic.arctic_connection import arcticData
from sysdata.production.historic_positions import strategyPositionData

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
        raise NotImplementedError

    def _delete_last_position_for_instrument_strategy_object_without_checking(
        self, instrument_strategy: instrumentStrategy
    ):
        raise NotImplementedError

    def _update_position_for_instrument_strategy_object_with_date(
        self,
        instrument_strategy: instrumentStrategy,
        position: int,
        date: datetime.datetime,
    ):

        raise NotImplementedError

    def get_position_as_series_for_instrument_strategy_object(
        self, instrument_strategy: instrumentStrategy
    ) -> pd.Series:

        raise NotImplementedError
