from syscore.objects import success
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen

from sysexecution.order_stack import orderStackData, missing_order
from sysexecution.base_orders import Order
from sysexecution.instrument_orders import instrumentOrder, instrumentOrderStackData
from sysexecution.contract_orders import contractOrder, contractOrderStackData
from sysexecution.broker_orders import brokerOrder, brokerOrderStackData

ORDER_ID_STORE_KEY = "_ORDER_ID_STORE_KEY"


class mongoOrderStackData(orderStackData):
    """
    Read and write data class to get roll state data


    """

    def _collection_name(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def _order_class(self):
        return Order

    def __init__(self, mongo_db=None, log=logtoscreen("mongoOrderStackData")):
        # Not needed as we don't store anything in _state attribute used in parent class
        # If we did have _state would risk breaking if we forgot to override methods
        # super().__init__()

        self._mongo = mongoConnection(
            self._collection_name(), mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("order_id")
        super().__init__(log=log)

    @property
    def _name(self):
        return "Generic order stack"

    def __repr__(self):
        return "Data connection for %s, mongodb %s/%s @ %s -p %s " % (
            self._name,
            self._mongo.database_name,
            self._mongo.collection_name,
            self._mongo.host,
            self._mongo.port,
        )

    def get_order_with_key_from_stack(self, order_key):
        result_dict = self._mongo.collection.find_one(
            dict(key=order_key, active=True))
        if result_dict is None:
            return missing_order
        result_dict.pop(MONGO_ID_KEY)

        order_class = self._order_class()
        order = order_class.from_dict(result_dict)
        return order

    def get_order_with_id_from_stack(self, order_id):
        result_dict = self._mongo.collection.find_one(dict(order_id=order_id))
        if result_dict is None:
            return missing_order
        result_dict.pop(MONGO_ID_KEY)

        order_class = self._order_class()
        order = order_class.from_dict(result_dict)
        return order

    def get_list_of_order_ids(self, exclude_inactive_orders=True):
        if exclude_inactive_orders:
            pass
        else:
            return self._get_list_of_all_order_ids()
        cursor = self._mongo.collection.find(dict(active=True))
        order_ids = [db_entry["order_id"] for db_entry in cursor]

        return order_ids

    def get_list_of_inactive_order_ids(self):
        cursor = self._mongo.collection.find(dict(active=False))
        order_ids = [db_entry["order_id"] for db_entry in cursor]

        return order_ids

    def _get_list_of_all_order_ids(self):
        cursor = self._mongo.collection.find()
        order_ids = [db_entry["order_id"] for db_entry in cursor]
        order_ids.remove(ORDER_ID_STORE_KEY)

        return order_ids

    def _change_order_on_stack_no_checking(self, order_id, order):
        self._mongo.collection.update_one(
            dict(order_id=order_id), {"$set": order.as_dict()}
        )

        return success

    def _put_order_on_stack_no_checking(self, order):
        mongo_record = order.as_dict()
        self._mongo.collection.insert_one(mongo_record)
        return success

    # ORDER ID
    def _get_next_order_id(self):
        max_orderid = self._get_current_max_order_id()
        new_orderid = max_orderid + 1
        self._update_max_order_id(new_orderid)

        return new_orderid

    def _get_current_max_order_id(self):
        result_dict = self._mongo.collection.find_one(
            dict(order_id=ORDER_ID_STORE_KEY))
        if result_dict is None:
            return self._create_max_order_id()

        result_dict.pop(MONGO_ID_KEY)
        order_id = result_dict["max_order_id"]

        return order_id

    def _update_max_order_id(self, max_order_id):
        self._mongo.collection.update_one(dict(order_id=ORDER_ID_STORE_KEY), {
            "$set": dict(max_order_id=max_order_id)})

        return success

    def _create_max_order_id(self):
        first_order_id = 1
        self._mongo.collection.insert_one(
            dict(order_id=ORDER_ID_STORE_KEY, max_order_id=first_order_id)
        )
        return first_order_id

    def _remove_order_with_id_from_stack_no_checking(self, order_id):
        self._mongo.collection.remove(dict(order_id=order_id))
        return success


class mongoInstrumentOrderStackData(
        mongoOrderStackData,
        instrumentOrderStackData):
    def _collection_name(self):
        return "INSTRUMENT_ORDER_STACK"

    def _order_class(self):
        return instrumentOrder

    @property
    def _name(self):
        return "Instrument order stack"


class mongoContractOrderStackData(mongoOrderStackData, contractOrderStackData):
    def _collection_name(self):
        return "CONTRACT_ORDER_STACK"

    def _order_class(self):
        return contractOrder

    @property
    def _name(self):
        return "Contract order stack"


class mongoBrokerOrderStackData(mongoOrderStackData, brokerOrderStackData):
    def _collection_name(self):
        return "BROKER_ORDER_STACK"

    def _order_class(self):
        return brokerOrder

    @property
    def _name(self):
        return "Broker order stack"
