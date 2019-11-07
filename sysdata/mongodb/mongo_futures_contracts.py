from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY

CONTRACT_COLLECTION = 'futures_contracts'
DEFAULT_DB = 'production'

from sysdata.futures.contracts import futuresContractData, futuresContract
from syslogdiag.log import logtoscreen

class mongoFuturesContractData(futuresContractData):
    """
    Read and write data class to get futures contract data

    We store instrument code, and contract date data (date, expiry, roll cycle)

    The keys used are a tuple CHECK instrument_code, contract_date

    If you want more information about a given instrument you have to read it in using mongoFuturesInstrumentData
    """

    def __init__(self, mongo_db = None, log=logtoscreen("mongoFuturesContractData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(CONTRACT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_multikey_index("instrument_code", "contract_date")

        self.name = "simData connection for futures contracts, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

    def __repr__(self):
        return self.name

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code):

        filter_by_code = {'instrument_code' : instrument_code}
        cursor = self._mongo.collection.find(filter_by_code)
        contract_dates = [db_entry['contract_date'] for db_entry in cursor]

        return contract_dates

    def _get_contract_data_without_checking(self, instrument_code, contract_date):

        result_dict = self._mongo.collection.find_one(dict(instrument_code=instrument_code, contract_date = contract_date))
        result_dict.pop(MONGO_ID_KEY)

        # NOTE: The instrument object inside this contract will be 'bare', with only the instrument code
        contract_object = futuresContract.create_from_dict(result_dict)

        return contract_object


    def _delete_contract_data_without_any_warning_be_careful(self, instrument_code, contract_date):
        self._mongo.collection.remove(dict(instrument_code=instrument_code, contract_date = contract_date))
        self.log.terse("Deleted %s %s from %s" % (instrument_code, contract_date, self.name))

    def _add_contract_object_without_checking_for_existing_entry(self, contract_object):
        self._mongo.collection.insert_one(contract_object.as_dict())
        self.log.terse("Added %s to %s" % (contract_object.ident, self.name))

