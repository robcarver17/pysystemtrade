
CONTRACT_COLLECTION = "futures_contracts"

from sysdata.futures.contracts import futuresContractData
from sysobjects.contracts import  contract_key_from_code_and_id, futuresContract, get_code_and_id_from_contract_key, key_contains_instrument_code, listOfFuturesContracts
from syslogdiag.log import logtoscreen
from sysdata.mongodb.mongo_generic import mongoData, missing_data

class mongoFuturesContractData(futuresContractData):
    """
    Read and write data class to get futures contract data

    We store instrument code, and contract date data (date, expiry, roll cycle)

    If you want more information about a given instrument you have to read it in using mongoFuturesInstrumentData
    """
    def __init__(self, mongo_db=None, log=logtoscreen(
            "mongoFuturesContractData")):

        super().__init__(log=log)
        mongo_data = mongoData(CONTRACT_COLLECTION, "contract_key", mongo_db = mongo_db)
        self._mongo_data = mongo_data

        any_old_data_was_modified = _from_old_to_new_contract_storage(mongo_data)
        if any_old_data_was_modified:
            self.log.critical("Modified the storage of contract data. Any other processes running will need restarting with new code")

    def __repr__(self):
        return "mongoFuturesInstrumentData %s" % str(self.mongo_data)

    @property
    def mongo_data(self):
        return self._mongo_data

    def is_contract_in_data(self, instrument_code:str, contract_id:str) -> bool:
        key = contract_key_from_code_and_id(instrument_code, contract_id)
        return self.mongo_data.key_is_in_data(key)

    def get_list_of_all_contract_keys(self) -> list:
        return self.mongo_data.get_list_of_keys()

    def get_all_contract_objects_for_instrument_code(self, instrument_code: str) -> listOfFuturesContracts:

        list_of_keys = self._get_all_contract_keys_for_instrument_code(instrument_code)
        list_of_objects = [self._get_contract_data_from_key_without_checking(key) for key in list_of_keys]
        list_of_futures_contracts = listOfFuturesContracts(list_of_objects)

        return list_of_futures_contracts

    def _get_all_contract_keys_for_instrument_code(self, instrument_code:str) -> list:
        list_of_all_contract_keys = self.get_list_of_all_contract_keys()
        list_of_relevant_keys = [contract_key
                                 for contract_key in list_of_all_contract_keys
                                 if key_contains_instrument_code(contract_key, instrument_code)]

        return list_of_relevant_keys

    def get_list_of_contract_dates_for_instrument_code(self, instrument_code:str) -> list:
        list_of_keys = self._get_all_contract_keys_for_instrument_code(instrument_code)
        list_of_split_keys = [get_code_and_id_from_contract_key(key) for key in list_of_keys]
        list_of_contract_id = [contract_id for _,contract_id in list_of_split_keys]

        return list_of_contract_id

    def _get_contract_data_without_checking(
            self, instrument_code:str, contract_id:str) -> futuresContract:

        key = contract_key_from_code_and_id(instrument_code, contract_id)
        contract_object = self._get_contract_data_from_key_without_checking(key)

        return contract_object

    def _get_contract_data_from_key_without_checking(
            self, key:str) ->futuresContract:

        result_dict = self.mongo_data.get_result_dict_for_key_without_key_value(key)
        if result_dict is missing_data:
            # shouldn't happen...
            raise Exception("Data for %s gone AWOL" % key)

        contract_object = futuresContract.create_from_dict(result_dict)

        return contract_object

    def _delete_contract_data_without_any_warning_be_careful(
        self, instrument_code:str, contract_date:str
    ):

        key =  contract_key_from_code_and_id(instrument_code, contract_date)
        self.mongo_data.delete_data_without_any_warning(key)

    def _add_contract_object_without_checking_for_existing_entry(
            self, contract_object: futuresContract):
        contract_object_as_dict = contract_object.as_dict()
        key = contract_object.key
        self.mongo_data.add_data(key, contract_object_as_dict, allow_overwrite=True)

###########################################################################
# THE FOLLOWING CODE IS USED ONLY TO TRANSLATE 'OLD STYLE' INTO 'NEW STYLE'
# IT WILL RUN ONCE ONLY, SO IN THE FUTURE IT CAN BE DELETED
###########################################################################

from sysdata.mongodb.mongo_connection import MONGO_ID_KEY


def _from_old_to_new_contract_storage(mongo_data):
    existing_records = mongo_data._mongo.collection.find()
    existing_records_as_list = [record for record in existing_records]
    list_of_old_records = [record for record in existing_records_as_list if _is_old_record(record)]

    if len(list_of_old_records)==0:
        return False

    mongo_data._mongo.collection.drop_indexes()

    _translate_old_records(mongo_data, list_of_old_records)

    mongo_data._mongo.create_index(mongo_data.key_name)

    return True

def _is_old_record(record):
    if "instrument_code" in list(record.keys()):
        return True
    else:
        return False

def _translate_old_records(mongo_data, list_of_old_records):
    _ = [_translate_record(mongo_data, record) for record in list_of_old_records]

    return None

def _translate_record(mongo_data, record):
    contract_object = _get_old_record(mongo_data, record)
    mongo_data.delete_data_without_any_warning(contract_object.key)
    mongo_data.add_data(contract_object.key, contract_object.as_dict())
    _delete_old_record(mongo_data, record)

def _get_old_record(mongo_data, record):
    instrument_code = record['instrument_code']
    contract_date = record['contract_date']
    result_dict = mongo_data._mongo.collection.find_one(
        dict(instrument_code=instrument_code, contract_date=contract_date)
    )
    result_dict.pop(MONGO_ID_KEY)

    contract_object = _from_old_style_mongo_record_to_contract_dict(result_dict)

    return contract_object


def _from_old_style_mongo_record_to_contract_dict(mongo_record_dict):
    """

    :param mongo_record_dict:
    :return: dict to pass to futuresContract.create_from_dict
    """

    mongo_record_dict.pop("instrument_code")
    mongo_record_dict.pop("contract_date")

    contract_object = futuresContract.create_from_dict(mongo_record_dict)

    return contract_object

def _delete_old_record(mongo_data, record):
    instrument_code = record['instrument_code']
    contract_date = record['contract_date']

    mongo_data._mongo.collection.delete_one(dict(instrument_code=instrument_code, contract_date=contract_date))


