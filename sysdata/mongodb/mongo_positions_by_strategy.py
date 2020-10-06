from sysdata.production.historic_positions import instrumentPositionData
from sysdata.mongodb.mongo_generic_timed_storage import mongoListOfEntriesData

POSITION_STRATEGY_COLLECTION = "futures_position_by_strategy"


class mongoStrategyPositionData(
        instrumentPositionData,
        mongoListOfEntriesData):
    """
    Read and write data class to get positions by strategy, per instrument


    """

    def _collection_name(self):
        return POSITION_STRATEGY_COLLECTION

    def _data_name(self):
        return "mongoStrategyPositionData"
