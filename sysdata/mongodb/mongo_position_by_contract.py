from sysdata.production.historic_positions import contractPositionData
from sysdata.mongodb.mongo_generic_timed_storage import mongoListOfEntriesData

POSITION_CONTRACT_COLLECTION = "futures_position_by_contract"


class mongoContractPositionData(contractPositionData, mongoListOfEntriesData):
    """
    Read and write data class to get positions by contract


    """

    def _collection_name(self):
        return POSITION_CONTRACT_COLLECTION

    def _data_name(self):
        return "mongoContractPositionData"
