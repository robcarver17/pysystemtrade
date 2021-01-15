from sysdata.production.optimal_positions import optimalPositionData
from sysdata.mongodb.mongo_timed_storage import mongoListOfEntriesData

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
