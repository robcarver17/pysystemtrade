import datetime

from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import Order, tradeableObject, no_order_id, no_children, no_parent, MODIFICATION_STATUS_NO_MODIFICATION
from syscore.genutils import  none_to_object, object_to_none

possible_order_types = ['best', 'market', 'limit', 'Zero-roll-order']

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
                 reference_datetime = None,
                 reference_price = None, reference_contract = None,
                 generated_datetime = None,
                 filled_price = None, fill_datetime = None,
                 manual_trade =False, roll_order = False):
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
        :param reference_datetime: datetime, when reference price captured
        :param fill_datetime: datetime used for p&l
        :param generated_datetime: when order generated
        :param manual_trade: bool, was trade iniated manually
        :param roll_order: bool, is this a roll order

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

        if generated_datetime is None:
            generated_datetime = datetime.datetime.now()

        self._trade = trade
        self._fill = fill
        self._fill_datetime = fill_datetime
        self._filled_price = filled_price
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
                                manual_trade = manual_trade,
                                roll_order = roll_order, reference_datetime = reference_datetime,
                                generated_datetime = generated_datetime)


    def __repr__(self):
        my_repr = super().__repr__()
        if self.filled_price is not None and self.fill_datetime is not None:
            my_repr = my_repr + "Fill %.2f on %s" % (self.filled_price, self.fill_datetime)
        my_repr = my_repr+" %s" % str(self._order_info)

        return my_repr

    def terse_repr(self):
        order_repr = super().__repr__()
        return order_repr

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        trade = order_as_dict.pop('trade')
        key = order_as_dict.pop('key')
        fill = order_as_dict.pop('fill')
        filled_price = order_as_dict.pop('filled_price')
        fill_datetime = order_as_dict.pop('fill_datetime')
        locked = order_as_dict.pop('locked')
        order_id = none_to_object(order_as_dict.pop('order_id'), no_order_id)
        modification_status = order_as_dict.pop('modification_status')
        modification_quantity = order_as_dict.pop('modification_quantity')
        parent = none_to_object(order_as_dict.pop('parent'), no_parent)
        children = none_to_object(order_as_dict.pop('children'), no_children)
        active = order_as_dict.pop('active')

        order_info = order_as_dict

        order = instrumentOrder(key, trade, fill=fill, locked = locked, order_id = order_id,
                      modification_status = modification_status,
                      modification_quantity = modification_quantity,
                      parent = parent, children = children,
                                fill_datetime = fill_datetime, filled_price=filled_price,
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
    def reference_datetime(self):
        return self._order_info['reference_datetime']

    @property
    def generated_datetime(self):
        return self._order_info['reference_datetime']

    @property
    def manual_trade(self):
        return self._order_info['manual_trade']

    @property
    def roll_order(self):
        return self._order_info['roll_order']


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