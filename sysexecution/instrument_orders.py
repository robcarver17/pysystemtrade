from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import Order, tradeableObject, no_order_id, no_children, no_parent, MODIFICATION_STATUS_NO_MODIFICATION
from syscore.genutils import  none_to_object, object_to_none

possible_order_types = ['best', 'market', 'limit']

class instrumentTradeableObject(tradeableObject):
    def __init__(self, strategy_name, instrument_code):
        dict_def = dict(strategy_name = strategy_name, instrument_code = instrument_code)
        self._set_definition(dict_def)

    @classmethod
    def from_key(instrumentTradeableObject, key):
        strategy_name, instrument_code = key.split("/")

        return instrumentTradeableObject(strategy_name, instrument_code)

    @property
    def strategy_name(self):
        return self._definition['strategy_name']

    @property
    def instrument_code(self):
        return self._definition['instrument_code']

    @property
    def key(self):
        return "/".join([self._definition['strategy_name'],self._definition['instrument_code']])


class instrumentOrder(Order):

    def __init__(self, *args, fill=0,
                 locked=False, order_id=no_order_id,
                 modification_status = MODIFICATION_STATUS_NO_MODIFICATION,
                 modification_quantity = None, parent=no_parent,
                 children=no_children, active=True,
                 order_type="best", limit_price = None, limit_contract = None,
                 reference_price = None, reference_contract = None,
                 filled_price = None, fill_datetime = None):
        """

        :param args: Eithier a single argument 'strategy/instrument' str, or strategy, instrument; followed by trade
        i.e. instrumentOrder(strategy, instrument, trade,  **kwargs) or 'strategy/instrument', trade, type, **kwargs)

        :param fill: fill done so far, int
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param modification_status: whether the order is being modified, str
        :param modification_quantity: The new quantity trade we want to do once modified, int
        :param parent: int, order ID of parent order in upward stack
        :param children: list of int, order IDs of child orders in downward stack
        :param active: bool, inactive orders have been filled or cancelled
        :param order_type: str, type of execution required
        :param limit_price: float, limit orders only
        :param limit_contract: YYYYMM string, contract that limit price references
        :param reference_price: float, used for execution calculations
        :param reference_contract: YYYYMM string, contract that relates to reference price
        :param filled_price: float, used for execution calculations and p&l
        :param fill_datetime: datetime used for p&l
        """

        """
        
        :param trade: float
        :param args: Eithier 2: strategy, instrument; or 1: instrumentTradeableObject
        :param type: str
        """
        if len(args)==2:
            self._tradeable_object = instrumentTradeableObject.from_key(args[0])
            trade = args[1]
        else:
            strategy=args[0]
            instrument = args[1]
            trade = args[2]
            self._tradeable_object = instrumentTradeableObject(strategy, instrument)

        self._trade = trade
        self._fill = fill
        self._locked = locked
        self._order_id = order_id
        self._modification_status = modification_status
        self._modification_quantity = modification_quantity
        self._parent = parent
        self._children = children
        self._active = active

        assert order_type in possible_order_types
        self._order_info = dict(order_type=order_type, limit_contract = limit_contract, limit_price = limit_price,
                               reference_contract = reference_contract, reference_price = reference_price,
                                filled_price = filled_price, fill_datetime = fill_datetime)


    def __repr__(self):
        order_repr = super().__repr__()
        my_repr = order_repr+" %s" % str(self._order_info)

        return my_repr

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        trade = order_as_dict.pop('trade')
        key = order_as_dict.pop('key')
        locked = order_as_dict.pop('locked')
        order_id = none_to_object(order_as_dict.pop('order_id'), no_order_id)
        modification_status = order_as_dict.pop('modification_status')
        modification_quantity = order_as_dict.pop('modification_quantity')
        parent = none_to_object(order_as_dict.pop('parent'), no_parent)
        children = none_to_object(order_as_dict.pop('children'), no_children)
        active = order_as_dict.pop('active')

        order_info = order_as_dict

        order = instrumentOrder(key, trade, locked = locked, order_id = order_id,
                      modification_status = modification_status,
                      modification_quantity = modification_quantity,
                      parent = parent, children = children,
                      active = active,
                      **order_info)

        return order

    @property
    def strategy_name(self):
        return self._tradeable_object.strategy_name

    @property
    def instrument_code(self):
        return self._tradeable_object.instrument_code

    @property
    def order_type(self):
        return self._order_info['order_type']

    @order_type.setter
    def order_type(self, order_type):
        self._order_info['order_type'] = order_type

    @property
    def limit_contract(self):
        return self._order_info['limit_contract']

    @limit_contract.setter
    def limit_contract(self, limit_contract):
        self._order_info['limit_contract'] = limit_contract

    @property
    def limit_price(self):
        return self._order_info['limit_price']

    @limit_price.setter
    def limit_price(self, limit_price):
        self._order_info['limit_price'] = limit_price

    @property
    def reference_contract(self):
        return self._order_info['reference_contract']

    @reference_contract.setter
    def reference_contract(self, reference_contract):
        self._order_info['reference_contract'] = reference_contract

    @property
    def reference_price(self):
        return self._order_info['reference_price']

    @reference_price.setter
    def reference_price(self, reference_price):
        self._order_info['reference_price'] = reference_price

    @property
    def filled_price(self):
        return self._order_info['filled_price']

    @filled_price.setter
    def filled_price(self, filled_price):
        self._order_info['filled_price'] = filled_price

    @property
    def fill_datetime(self):
        return self._order_info['fill_datetime']

    @fill_datetime.setter
    def fill_datetime(self, fill_datetime):
        self._order_info['fill_datetime'] = fill_datetime



class instrumentOrderStackData(orderStackData):
    def __repr__(self):
        return "Instrument order stack: %s" % str(self._stack)

    def view_order_for_strategy_and_instrument(self, strategy_name, instrument_code):
        tradeable_object = instrumentTradeableObject(strategy_name, instrument_code)
        key = tradeable_object.key

        return self.get_order_with_key_from_stack(key)

def log_attributes_from_instrument_order(log, instrument_order):
    """
    Returns a new log object with instrument_order attributes added

    :param log: logger
    :param instrument_order:
    :return: log
    """
    new_log = log.setup(
              strategy_name=instrument_order.strategy_name,
              instrument_code=instrument_order.instrument_code,
              instrument_order_id=object_to_none(instrument_order.order_id, no_order_id))

    return new_log