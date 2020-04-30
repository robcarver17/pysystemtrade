from syscore.objects import success
from sysdata.production.position_by_contract_state import positionByContractData, no_position_available

from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen

POSITION_CONTRACT_STATUS_COLLECTION = 'futures_position_by_contract_status'

class mongoPositionByContractData(positionByContractData):
    """
    Read and write data class to get positions by contract


    """

    def __init__(self, mongo_db = None, log=logtoscreen("mongoPositionByContractData")):

        super().__init__(log=log)

        self._mongo = mongoConnection(POSITION_CONTRACT_STATUS_COLLECTION, mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_multikey_index("instrument_code", "contract_date")

        self.name = "Data connection for futures contracts position state, mongodb %s/%s @ %s -p %s " % (
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

    def __repr__(self):
        return self.name

    def _keys_given_contract_object(self, futures_contract_object):
        """
        To enforce uniqueness, we index seperately on code and object date

        :param futures_contract_object: futuresContract
        :return: str
        """

        return futures_contract_object.instrument_code, futures_contract_object.date


    def get_list_of_instruments(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry['instrument_code'] for db_entry in cursor]

        return codes

    def get_list_of_contracts_with_positions(self, instrument_code):
        cursor = self._mongo.collection.find(dict(instrument_code=instrument_code))
        list_of_contracts = []
        for result_dict in cursor:
            contract_id = result_dict['contract_date']
            list_of_contracts.append(contract_id)

        return list_of_contracts

    def _get_position_for_contract_no_default(self, futures_contract_object):
        instrument_code, contract_date = self._keys_given_contract_object(futures_contract_object)
        result_dict = self._mongo.collection.find_one(dict(instrument_code=instrument_code, contract_date=contract_date))
        if result_dict is None:
            return no_position_available
        result_dict.pop(MONGO_ID_KEY)

        position = int(result_dict['position'])

        return position

    def update_position(self, futures_contract_object, new_position):
        instrument_code, contract_date = self._keys_given_contract_object(futures_contract_object)
        new_position_as_float = float(new_position) # mongo doesn't like ints
        find_object_dict = dict(instrument_code = instrument_code, contract_date = contract_date)
        new_values_dict = {"$set": {"position": new_position_as_float}}
        self._mongo.collection.update_one(find_object_dict, new_values_dict, upsert=True)
        self.log.terse("Updated position of %s/%s to %s in %s" % (instrument_code, contract_date, new_position, self.name))

        return success
