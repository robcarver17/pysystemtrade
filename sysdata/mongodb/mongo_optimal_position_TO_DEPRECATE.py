from sysdata.production.optimal_positions_TO_DEPRECATE import optimalPositionData
from sysdata.mongodb.mongo_timed_storage_TO_DEPRECATE import mongoListOfEntriesData

OPTIMAL_POSITION_COLLECTION = "optimal_positions"


class mongoOptimalPositionData(optimalPositionData, mongoListOfEntriesData):
    """
    Read and write data class to get optimal positions for ecah strategy


    """

    @property
    def _collection_name(self):
        return OPTIMAL_POSITION_COLLECTION

    @property
    def _data_name(self):
        return "mongoOptimalPositionData"
