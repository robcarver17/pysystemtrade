from sysdata.production.capital import capitalData
from sysdata.mongodb.mongo_generic_timed_storage import mongoListOfEntriesData

CAPITAL_COLLECTION = "capital"


class mongoCapitalData(capitalData, mongoListOfEntriesData):
    """
    Read and write data class to get capital for each strategy


    """

    def _collection_name(self):
        return CAPITAL_COLLECTION

    def _data_name(self):
        return "mongoCapitalData"
