import datetime

from syscore.objects import success, missing_order, resolve_function, arg_not_supplied
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen
from sysdata.production.historic_orders import (
    genericOrdersData,
    strategyHistoricOrdersData,
    contractHistoricOrdersData,
)
from sysexecution.contract_orders import contractTradeableObject
from sysexecution.instrument_orders import instrumentTradeableObject

ORDER_ID_STORE_KEY = "_ORDER_ID_STORE_KEY"


class mongoGenericHistoricOrdersData(genericOrdersData):
    """
    Read and write data class to get roll state data


    """

    def _collection_name(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def _order_class_str(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def _order_class(self):
        class_as_str = self._order_class_str()
        return resolve_function(class_as_str)

    def __init__(
        self, mongo_db=None, log=logtoscreen("mongoGenericHistoricOrdersData")
    ):
        # Not needed as we don't store anything in _state attribute used in parent class
        # If we did have _state would risk breaking if we forgot to override methods
        # super().__init__()

        self._mongo = mongoConnection(
            self._collection_name(), mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("order_id")
        super().__init__(log = log)

    @property
    def _name(self):
        return "Generic historic orders"

    def __repr__(self):
        return "Data connection for %s, mongodb %s/%s @ %s -p %s " % (
            self._name,
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def add_order_to_data(self, order, ignore_duplication=False):
        # Duplicates will be overriden, so be careful
        order_id = order.order_id
        if self.get_order_with_orderid(order_id) is missing_order:
            return self._add_order_to_data_no_checking(order)
        if ignore_duplication:
            return self.update_order_with_orderid(order_id, order)
        else:
            raise Exception(
                "Can't add order %s as order id %d already exists!"
                % (str(order), order_id)
            )

    def _add_order_to_data_no_checking(self, order):
        # Duplicates will be overriden, so be careful
        mongo_record = order.as_dict()
        self._mongo.collection.insert_one(mongo_record)
        return success

    def get_order_with_orderid(self, order_id):
        result_dict = self._mongo.collection.find_one(dict(order_id=order_id))
        if result_dict is None:
            return missing_order
        result_dict.pop(MONGO_ID_KEY)

        order_class = self._order_class()
        order = order_class.from_dict(result_dict)
        return order

    def delete_order_with_orderid(self, order_id):
        self._mongo.collection.remove(dict(order_id=order_id))
        return success

    def update_order_with_orderid(self, order_id, order):
        self._mongo.collection.update_one(
            dict(order_id=order_id), {"$set": order.as_dict()}
        )

    def get_list_of_order_ids(self):
        cursor = self._mongo.collection.find()
        order_ids = [db_entry["order_id"] for db_entry in cursor]

        return order_ids

    def get_orders_in_date_range(
            self,
            period_start,
            period_end=arg_not_supplied):
        if period_end is arg_not_supplied:
            period_end = datetime.datetime.now()
        cursor = self._mongo.collection.find(
            dict(fill_datetime={"$gte": period_start, "$lt": period_end})
        )

        order_ids = [db_entry["order_id"] for db_entry in cursor]

        return order_ids


class mongoStrategyHistoricOrdersData(
    mongoGenericHistoricOrdersData, strategyHistoricOrdersData
):
    def _collection_name(self):
        return "_STRATEGY_HISTORIC_ORDERS"

    def _order_class_str(self):
        return "sysexecution.instrument_orders.instrumentOrder"

    def get_list_of_order_ids_for_strategy_and_instrument_code(
        self, strategy_name, instrument_code
    ):
        tradeable_object = instrumentTradeableObject(
            strategy_name, instrument_code)
        object_key = tradeable_object.key
        result_dict = self._mongo.collection.find(dict(key=object_key))
        list_of_order_id = [result["order_id"] for result in result_dict]
        return list_of_order_id


class mongoContractHistoricOrdersData(
    mongoGenericHistoricOrdersData, contractHistoricOrdersData
):
    def _collection_name(self):
        return "_CONTRACT_HISTORIC_ORDERS"

    def _order_class_str(self):
        return "sysexecution.broker_orders.contractOrder"

    def get_list_of_order_ids_for_strategy_and_contract(
        self, strategy_name, contract_object
    ):
        instrument_code = contract_object.instrument_code
        contract_id = contract_object.date_str

        tradeable_object = contractTradeableObject(
            strategy_name, instrument_code, contract_id
        )
        object_key = tradeable_object.key
        result_dict = self._mongo.collection.find(dict(key=object_key))
        list_oforder_id = [result["order_id"] for result in result_dict]

        alt_key = tradeable_object.alt_key
        result_dict = self._mongo.collection.find(dict(key=alt_key))
        alt_list_oforder_id = [result["order_id"] for result in result_dict]

        list_oforder_id = list_oforder_id + alt_list_oforder_id

        return list_oforder_id

    def get_list_of_all_keys(self):
        result_dict = self._mongo.collection.find()
        key_list = [result["key"] for result in result_dict]

        return key_list


class mongoBrokerHistoricOrdersData(
    mongoGenericHistoricOrdersData, contractHistoricOrdersData
):
    def _collection_name(self):
        return "_BROKER_HISTORIC_ORDERS"

    def _order_class_str(self):
        return "sysexecution.broker_orders.brokerOrder"
