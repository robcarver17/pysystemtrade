from sysdata.mongodb.mongo_connection import (
    mongoConnection,
    MONGO_ID_KEY,
    create_update_dict,
)

CONTRACT_COLLECTION = "futures_contracts"
DEFAULT_DB = "production"

from sysdata.futures.contracts import futuresContractData, futuresContract
from syslogdiag.log import logtoscreen


class mongoFuturesContractData(futuresContractData):
    """
    Read and write data class to get futures contract data

    We store instrument code, and contract date data (date, expiry, roll cycle)

    The keys used are a tuple CHECK instrument_code, contract_date

    If you want more information about a given instrument you have to read it in using mongoFuturesInstrumentData
    """

    def __init__(
            self,
            mongo_db=None,
            log=logtoscreen("mongoFuturesContractData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(CONTRACT_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_multikey_index("instrument_code", "contract_date")

        self.name = (
            "simData connection for futures contracts, mongodb %s/%s @ %s -p %s " %
            (self._mongo.database_name,
             self._mongo.collection_name,
             self._mongo.host,
             self._mongo.port,
             ))

    def __repr__(self):
        return self.name

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code):

        filter_by_code = {"instrument_code": instrument_code}
        cursor = self._mongo.collection.find(filter_by_code)
        contract_dates = [db_entry["contract_date"] for db_entry in cursor]

        return contract_dates

    def _get_contract_data_without_checking(
            self, instrument_code, contract_date):

        result_dict = self._mongo.collection.find_one(
            dict(instrument_code=instrument_code, contract_date=contract_date)
        )
        result_dict.pop(MONGO_ID_KEY)

        contract_object = from_mongo_record_to_contract_dict(result_dict)

        return contract_object

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code, contract_date
    ):
        self._mongo.collection.remove(
            dict(instrument_code=instrument_code, contract_date=contract_date)
        )
        self.log.terse("Deleted %s %s from %s" %
                       (instrument_code, contract_date, self.name))

    def add_contract_data(self, contract_object, ignore_duplication=False):

        instrument_code = contract_object.instrument_code
        contract_date = contract_object.date

        self.log.label(
            instrument_code=instrument_code,
            contract_date=contract_date)
        mongo_record = from_futures_contract_to_mongo_record_dict(
            contract_object)

        if self.is_contract_in_data(instrument_code, contract_date):
            if ignore_duplication:
                # exists in data but it's cool
                self.log.msg(
                    "Deleting %s/%s to write new record"
                    % (instrument_code, contract_date)
                )
                self.delete_contract_data(
                    instrument_code, contract_date, are_you_sure=True
                )
            else:
                self.log.warn(
                    "There is already %s/%s in the data, you have to delete it first" %
                    (instrument_code, contract_date))
                return None

        # isn't in date, can use insert
        self._mongo.collection.insert_one(mongo_record)

        self.log.terse(
            "Added contract %s %s" %
            (instrument_code, contract_date))


def from_mongo_record_to_contract_dict(mongo_record_dict):
    """
    Mongo records contain additional entries: instrument_code, contract_date
    These are embedded within the nested dicts, so strip out

    :param mongo_record_dict:
    :return: dict to pass to futuresContract.create_from_dict
    """

    mongo_record_dict.pop("instrument_code")
    mongo_record_dict.pop("contract_date")

    contract_object = futuresContract.create_from_dict(mongo_record_dict)

    return contract_object


def from_futures_contract_to_mongo_record_dict(futures_contract):
    """
    Mongo records contain additional entries: instrument_code, contract_date
    These are embedded within the nested dicts

    :param futures_contract: futuresContract
    :return: dict to write in mongo
    """

    instrument_code = futures_contract.instrument_code
    contract_date_id = futures_contract.date

    mongo_record = futures_contract.as_dict()
    mongo_record["instrument_code"] = instrument_code
    mongo_record["contract_date"] = contract_date_id

    return mongo_record
