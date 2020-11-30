from syscore.objects import missing_data
from sysdata.production.trade_limits import (
    tradeLimitData,
    tradeLimit,
    listOfTradeLimits,
)
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen

LIMIT_STATUS_COLLECTION = "limit_status"


class mongoTradeLimitData(tradeLimitData):
    """
    Read and write data class to get override state data


    """

    def __init__(self, mongo_db=None, log=logtoscreen("mongoTradeLimitData")):
        super().__init__(log=log)

        self._mongo = mongoConnection(
            LIMIT_STATUS_COLLECTION, mongo_db=mongo_db)

        self.name = (
            "Data connection for trade limit data, mongodb %s/%s @ %s -p %s "
            % (
                self._mongo.database_name,
                self._mongo.collection_name,
                self._mongo.host,
                self._mongo.port,
            )
        )

    def __repr__(self):
        return self.name

    def get_all_limits(self):
        cursor = self._mongo.collection.find()

        result = self._get_list_of_trade_limits_for_cursor(cursor)

        return result

    def get_list_of_trade_limits_for_strategy_instrument(
        self, strategy_name, instrument_code
    ):
        find_object_dict = dict(
            strategy_name=strategy_name, instrument_code=instrument_code
        )
        cursor = self._mongo.collection.find(find_object_dict)

        result = self._get_list_of_trade_limits_for_cursor(cursor)

        return result

    def _get_list_of_trade_limits_for_cursor(self, cursor):

        list_of_dicts = [db_entry for db_entry in cursor]
        _ = [db_entry.pop(MONGO_ID_KEY) for db_entry in list_of_dicts]
        trade_limits = [(tradeLimit.from_dict(db_dict))
                        for db_dict in list_of_dicts]

        list_of_trade_limits = listOfTradeLimits(trade_limits)

        return list_of_trade_limits

    def _get_all_limit_keys(self):
        raise NotImplementedError

    def _get_trade_limit_object_or_missing_data(
        self, strategy_name, instrument_code, period_days
    ):
        result_dict = self._mongo.collection.find_one(
            dict(
                strategy_name=strategy_name,
                instrument_code=instrument_code,
                period_days=period_days,
            )
        )
        if result_dict is None:
            return missing_data
        result_dict.pop(MONGO_ID_KEY)
        trade_limit = tradeLimit.from_dict(result_dict)

        return trade_limit

    def _update_trade_limit_object(self, trade_limit_object):
        strategy_name = trade_limit_object.strategy_name
        instrument_code = trade_limit_object.instrument_code
        period_days = trade_limit_object.period_days

        if (
            self._get_trade_limit_object_or_missing_data(
                strategy_name, instrument_code, period_days
            )
            is missing_data
        ):
            return self._add_new_trade_limit_object(trade_limit_object)
        else:
            return self._change_existing_trade_limit_object(trade_limit_object)

    def _change_existing_trade_limit_object(self, trade_limit_object):
        strategy_name = trade_limit_object.strategy_name
        instrument_code = trade_limit_object.instrument_code
        period_days = trade_limit_object.period_days

        self.log.msg("Updating trade limit to %s" % trade_limit_object)

        find_object_dict = dict(
            strategy_name=strategy_name,
            instrument_code=instrument_code,
            period_days=period_days,
        )
        new_values_dict = {"$set": trade_limit_object.as_dict()}
        self._mongo.collection.update_one(
            find_object_dict, new_values_dict, upsert=True
        )

    def _add_new_trade_limit_object(self, trade_limit_object):
        self.log.msg("Adding trade limit to %s" % trade_limit_object)

        object_dict = trade_limit_object.as_dict()
        self._mongo.collection.insert_one(object_dict)
