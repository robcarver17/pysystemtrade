from sysdata.production.historic_positions import strategyPositionData
from sysdata.mongodb.mongo_timed_storage import mongoListOfEntriesData

POSITION_STRATEGY_COLLECTION = "futures_position_by_strategy"


class mongoStrategyPositionData(strategyPositionData, mongoListOfEntriesData):
    """
    Read and write data class to get positions by strategy, per instrument


    """

    @property
    def _collection_name(self):
        return POSITION_STRATEGY_COLLECTION

    @property
    def _data_name(self):
        return "mongoStrategyPositionData"
