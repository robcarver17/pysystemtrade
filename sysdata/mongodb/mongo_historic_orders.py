from syscore.objects import success, missing_order, resolve_function
from sysdata.mongodb.mongo_connection import mongoConnection, MONGO_ID_KEY
from syslogdiag.log import logtoscreen
from sysdata.production.historic_orders import genericOrdersData, strategyHistoricOrdersData, contractHistoricOrdersData

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


    def __init__(self, mongo_db = None, log=logtoscreen("mongoGenericHistoricOrdersData")):
        # Not needed as we don't store anything in _state attribute used in parent class
        # If we did have _state would risk breaking if we forgot to override methods
        #super().__init__()

        self._mongo = mongoConnection(self._collection_name(), mongo_db=mongo_db)

        # this won't create the index if it already exists
        self._mongo.create_index("order_id")
        self.log = log

    @property
    def _name(self):
        return "Generic historic orders"

    def __repr__(self):
        return "Data connection for %s, mongodb %s/%s @ %s -p %s " % (self._name,
            self._mongo.database_name, self._mongo.collection_name, self._mongo.host, self._mongo.port)

    def add_order_to_data(self, order):
        # Doesn't check for duplicates
        order_id = self._get_next_order_id()
        order.order_id = order_id
        mongo_record = order.as_dict()
        self._mongo.collection.insert_one(mongo_record)
        return success


    def get_order_with_orderid(self, order_id):
        result_dict = self._mongo.collection.find_one(dict(order_id = order_id))
        if result_dict is None:
            return missing_order
        result_dict.pop(MONGO_ID_KEY)

        order_class = self._order_class()
        order = order_class.from_dict(result_dict)
        return order

    def delete_order_with_orderid(self, order_id):
        pass

    def update_order_with_orderid(self, order_id, order):
        self._mongo.collection.update_one(dict(order_id=order_id), {'$set': order.as_dict()})


    def get_list_of_order_ids(self):
        cursor = self._mongo.collection.find()
        order_ids = [db_entry['order_id'] for db_entry in cursor]
        order_ids.remove(ORDER_ID_STORE_KEY)

        return order_ids



    # ORDER ID
    def _get_next_order_id(self):
        max_orderid = self._get_current_max_order_id()
        new_orderid = max_orderid + 1
        self._update_max_order_id(new_orderid)

        return new_orderid

    def _get_current_max_order_id(self):
        result_dict = self._mongo.collection.find_one(dict(order_id=ORDER_ID_STORE_KEY))
        if result_dict is None:
            return self._create_max_order_id()

        result_dict.pop(MONGO_ID_KEY)
        order_id = result_dict['max_order_id']

        return order_id

    def _update_max_order_id(self, max_order_id):
        self._mongo.collection.update_one(dict(order_id=ORDER_ID_STORE_KEY), {'$set': dict(max_order_id=max_order_id)})

        return success

    def _create_max_order_id(self):
        first_order_id = 1
        self._mongo.collection.insert_one(dict(order_id=ORDER_ID_STORE_KEY, max_order_id=first_order_id))
        return first_order_id


class mongoStrategyHistoricOrdersData(mongoGenericHistoricOrdersData, strategyHistoricOrdersData):
    def _collection_name(self):
        return "_STRATEGY_HISTORIC_ORDERS"

    def _order_class_str(self):
        return "sysdata.production.historic_orders.historicStrategyOrder"

    def get_list_of_orders_for_strategy(self, strategy_name):
        raise NotImplementedError

    def get_list_of_orders_for_strategy_and_instrument(self, strategy_name, instrument_code):
        raise NotImplementedError

class mongoContractHistoricOrdersData(mongoGenericHistoricOrdersData, contractHistoricOrdersData):
    def _collection_name(self):
        return "_CONTRACT_HISTORIC_ORDERS"

    def _order_class_str(self):
        return "sysdata.production.historic_orders.historicContractOrder"

    def get_list_of_orders_since_date(self, recent_datetime):
        raise NotImplementedError
