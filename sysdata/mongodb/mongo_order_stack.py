from syscore.objects import success
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY, mongo_clean_ints
from syslogdiag.log import logtoscreen

from sysexecution.order_stack import orderStackData, Order, missing_order
from sysexecution.instrument_orders import instrumentOrder, instrumentOrderStackData

ORDER_ID_STORE_KEY = "_ORDER_ID_STORE_KEY"

class mongoOrderStackData(orderStackData):
    """
    Read and write data class to get roll state data


    """
    def _collection_name(self):
        raise NotImplementedError("Need to inherit for a specific data type")

    def _order_class(self):
        return Order

    def __init__(self, mongo_db = None, log=logtoscreen("mongoOrderStackData")):
        # Not needed as we don't store anything in _state attribute used in parent class
        # If we did have _state would risk breaking if we forgot to override methods
        #super().__init__()

        self._mongo = mongoConnection(self._collection_name(), mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("key")

    @property
    def _name(self):
        return "Generic order stack"

    def __repr__(self):
        return "Data connection for %s, mongodb %s/%s @ %s -p %s " % (self._name,
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

    def _modify_order_on_stack_no_checking(self, order):
        self._mongo.collection.update_one(dict(key = order.key), {'$set':order.as_dict()})
        return success

    def _get_next_order_id(self):
        max_orderid = self._get_current_max_order_id()
        new_orderid = max_orderid + 1
        self._update_max_order_id(new_orderid)

        return new_orderid

    def _get_current_max_order_id(self):
        result_dict = self._mongo.collection.find_one(dict(key=ORDER_ID_STORE_KEY))
        if result_dict is None:
            return self._create_max_order_id()

        result_dict.pop(MONGO_ID_KEY)
        order_id = result_dict['max_order_id']

        return order_id

    def _update_max_order_id(self, max_order_id):
        self._mongo.collection.update_one(dict(key=ORDER_ID_STORE_KEY), {'$set': dict(max_order_id=max_order_id)})

        return success

    def _create_max_order_id(self):
        first_order_id = 1
        self._mongo.collection.insert_one(dict(key=ORDER_ID_STORE_KEY, max_order_id=first_order_id))
        return first_order_id

    def _put_order_on_stack_no_checking(self, order):
        mongo_record = order.as_dict()
        self._mongo.collection.insert_one(mongo_record)
        return success

    def get_order_with_key_from_stack(self, order_key):
        result_dict = self._mongo.collection.find_one(dict(key = order_key))
        if result_dict is None:
            return missing_order
        result_dict.pop(MONGO_ID_KEY)

        order_class = self._order_class()
        order = order_class.from_dict(result_dict)
        return order

    def _remove_order_with_key_from_stack_no_checking(self, order_key):
        self._mongo.collection.remove(dict(key=order_key))
        return success

    def get_list_of_order_keys(self):
        cursor = self._mongo.collection.find()
        codes = [db_entry['key'] for db_entry in cursor]
        codes.remove(ORDER_ID_STORE_KEY)

        return codes

    def _empty_stack_without_checking(self):
        # probably will be overriden in data implementation
        self._mongo.collection.drop()

        return success

class mongoInstrumentOrderStackData(mongoOrderStackData, instrumentOrderStackData):
    def _collection_name(self):
        return 'INSTRUMENT_ORDER_STACK'

    def _order_class(self):
        return instrumentOrder

    @property
    def _name(self):
        return "Instrument order stack"

