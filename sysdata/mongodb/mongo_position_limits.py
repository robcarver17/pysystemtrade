from syscore.objects import missing_data

from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from sysdata.production.position_limits import positionLimitData, positionLimitForInstrument, positionLimitForStrategyInstrument

from syslogdiag.log import logtoscreen

POSITION_LIMIT_STATUS_COLLECTION = "position_limit_status"
MARKER_KEY = "marker"
MARKER_STRATEGY_INSTRUMENT = "strategy_instrument"
MARKER_INSTRUMENT = "instrument"

class mongoPositionLimitData(positionLimitData):
    """
    Read and write data class to get override state data


    """

    def __init__(self, mongo_db=None, log=logtoscreen("mongoPositionLimitData")):
        super().__init__(log=log)

        self._mongo = mongoConnection(
            POSITION_LIMIT_STATUS_COLLECTION, mongo_db=mongo_db)

        self.name = (
            "Data connection for position limit data, mongodb %s/%s @ %s -p %s "
            % (
                self._mongo.database_name,
                self._mongo.collection_name,
                self._mongo.host,
                self._mongo.port,
            )
        )

    def __repr__(self):
        return self.name

    def get_all_instruments_with_limits(self) -> list:
        pos_dict = dict(marker=MARKER_INSTRUMENT)
        cursor = self._mongo.collection.find(pos_dict)
        list_of_dicts = [db_entry for db_entry in cursor]
        list_of_instruments = [db_entry['instrument_code'] for db_entry in list_of_dicts]

        return list_of_instruments

    def get_all_strategy_instruments_with_limits(self) -> list:
        pos_dict = dict(marker=MARKER_STRATEGY_INSTRUMENT)
        cursor = self._mongo.collection.find(pos_dict)
        list_of_dicts = [db_entry for db_entry in cursor]
        list_of_strategy_instruments = [(db_entry['strategy_name'], db_entry['instrument_code']) for db_entry in list_of_dicts]

        return list_of_strategy_instruments

    def delete_abs_position_limit_for_strategy_instrument(self, strategy_name:str,
                                                       instrument_code: str):
        delete_dict = dict(marker = MARKER_STRATEGY_INSTRUMENT,
            strategy_name=strategy_name, instrument_code=instrument_code
        )
        self._mongo.collection.delete_one(delete_dict)

    def delete_position_limit_for_instrument(self, instrument_code: str):
        delete_dict = dict(marker = MARKER_INSTRUMENT,
            instrument_code=instrument_code
        )
        self._mongo.collection.delete_one(delete_dict)

    def _get_abs_position_limit_for_strategy_instrument(self,
                                                       strategy_name:
                                                       str, instrument_code: str) ->int:
        # return missing_data if no limit found
        find_object_dict = dict(marker = MARKER_STRATEGY_INSTRUMENT,
            strategy_name=strategy_name, instrument_code=instrument_code
        )
        position_limit = self._get_position_limit_from_dict(find_object_dict)

        return position_limit

    def _get_abs_position_limit_for_instrument(self,
                                              instrument_code: str,
                                              ) -> int:
        # return missing_data if no limit found
        find_object_dict = dict(marker = MARKER_INSTRUMENT,
            instrument_code=instrument_code
        )

        position_limit = self._get_position_limit_from_dict(find_object_dict)

        return position_limit

    def _get_position_limit_from_dict(self, find_object_dict: dict):
        cursor = self._mongo.collection.find_one(find_object_dict)
        if cursor is None:
            return missing_data
        position_limit = cursor['position_limit']

        return position_limit


    def set_position_limit_for_strategy_instrument(self, strategy_name:str,
                                                       instrument_code: str,
                                                       new_position_limit: int):

        pos_dict = dict(marker = MARKER_STRATEGY_INSTRUMENT, strategy_name = strategy_name,
                        instrument_code = instrument_code)

        self._set_position_limit_from_dict(pos_dict, new_position_limit)

    def set_position_limit_for_instrument(self, instrument_code: str,
                                              new_position_limit: int):
        pos_dict = dict(marker=MARKER_INSTRUMENT,
                        instrument_code=instrument_code)

        self._set_position_limit_from_dict(pos_dict, new_position_limit)

    def _set_position_limit_from_dict(self, pos_dict: dict,
                                      position_limit: int):

        existing_position_limit = self._get_position_limit_from_dict(pos_dict)
        if existing_position_limit is missing_data:
            self._add_new_position_limit(pos_dict, position_limit)
        else:
            self._change_existing_position_limit(pos_dict, position_limit)




    def _add_new_position_limit(self, pos_dict:dict , position_limit: int):
        pos_dict['position_limit'] = position_limit

        self.log.msg("Adding position limit %s" % str(pos_dict))

        self._mongo.collection.insert_one(pos_dict)

    def _change_existing_position_limit(self, pos_dict:dict, position_limit: int):

        self.log.msg("Updating trade limit %s to %d" % (str(pos_dict), position_limit))

        new_values_dict = {"$set": dict(position_limit = position_limit)}
        self._mongo.collection.update_one(
            pos_dict, new_values_dict, upsert=True
        )


