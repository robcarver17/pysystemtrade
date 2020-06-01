
from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import Order,  no_order_id, no_children, no_parent, MODIFICATION_STATUS_NO_MODIFICATION
from sysexecution.contract_orders import contractTradeableObject
from syscore.genutils import  none_to_object, object_to_none
from syscore.objects import failure, success, arg_not_supplied


class brokerOrder(Order):

    def __init__(self, *args, fill=0,
                 locked=False, order_id=no_order_id,
                 modification_status = MODIFICATION_STATUS_NO_MODIFICATION,
                 modification_quantity = None, parent=no_parent,
                 children=no_children, active=True,
                 algo_used="", filled_price = None,
                 limit_price = None):

        """
        :param args: Eithier a single argument 'strategy/instrument/contract_id' str, or strategy, instrument, contract_id; followed by trade
        i.e. contractOrder(strategy, instrument, contractid, trade,  **kwargs) or 'strategy/instrument/contract_id', trade, type, **kwargs)

        Contract_id can eithier be a single str or a list of str for spread orders, all YYYYMM
        If expressed inside a longer string, seperate contract str by '_'

        i.e. contractOrder('a strategy', 'an instrument', '201003', 6,  **kwargs)
         same as contractOrder('a strategy/an instrument/201003', 6,  **kwargs)
        contractOrder('a strategy', 'an instrument', ['201003', '201406'], [6,-6],  **kwargs)
          same as contractOrder('a strategy/an instrument/201003_201406', [6,-6],  **kwargs)

        :param fill: fill done so far, list of int
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param modification_status: whether the order is being modified, str
        :param modification_quantity: The new quantity trade we want to do once modified, int
        :param parent: int, order ID of parent order in upward stack
        :param children: list of int, order IDs of child orders in downward stack
        :param active: bool, inactive orders have been filled or cancelled
        :param algo_to_use: str, type of execution required
        :param limit_price: float, limit orders only
        :param reference_price: float, used to benchmark order (usually price from previous days close)
        :param execution_details: list of dicts, containing the execution history of the order (broker level)

    def __init__(self, strategy_name="", instrument_code="", contract_id="", quantity_filled=0,
                 filled_price=arg_not_supplied, order_id=arg_not_supplied,
                 order_type="best",
                 limit_price = arg_not_supplied, reference_price = arg_not_supplied, side_price = arg_not_supplied,
                 offside_price = arg_not_supplied,
                 linked_instrument_order = arg_not_supplied, algo_used = "",
                 algo_state="",
                 broker = "", broker_account = "", broker_clientid = "",
                 commission = 0.0,
                 reference_datetime= arg_not_supplied, submit_datetime = arg_not_supplied, fill_datetime = arg_not_supplied,
                 broker_permid = "", broker_tempid = "",
                 manual_fill = False,
                 manual_trade = False,
                 roll_order = False,
                 inter_spread_order = False,
                 calendar_spread_order = False,
                 linked_spread_orders = [],

                 comment = ""

        """
        if len(args)==2:
            self._tradeable_object = contractTradeableObject.from_key(args[0])
            trade = args[1]
        elif len(args)==4:
            strategy=args[0]
            instrument = args[1]
            contract_id = args[2]
            trade = args[3]
            self._tradeable_object = contractTradeableObject(strategy, instrument, contract_id)
        else:
            raise Exception("contractOrder(strategy, instrument, contractid, trade,  **kwargs) or ('strategy/instrument/contract_id', trade, **kwargs) ")

        if type(trade) is int:
            trade = [trade]
        self._trade = trade
        self._fill = fill
        self._locked = locked
        self._order_id = order_id
        self._modification_status = modification_status
        self._modification_quantity = modification_quantity
        self._parent = parent
        self._children = children
        self._active = active
        self._order_info = dict(algo_to_use=algo_to_use, reference_price=reference_price,
                 limit_price = limit_price, execution_details = execution_details)

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

        order = contractOrder(key, trade, locked = locked, order_id = order_id,
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
    def contract_id(self):
        return self._tradeable_object.contract_id

    @property
    def contract_id_key(self):
        return self._tradeable_object.contract_id_key

    @property
    def algo_to_use(self):
        return self._order_info['algo_to_use']

    @algo_to_use.setter
    def algo_to_use(self, algo_to_use):
        self._order_info['algo_to_use'] = algo_to_use

    @property
    def reference_price(self):
        return self._order_info['reference_price']

    @reference_price.setter
    def reference_price(self, reference_price):
        self._order_info['reference_price'] = reference_price

    @property
    def limit_price(self):
        return self._order_info['limit_price']

    @limit_price.setter
    def limit_price(self, limit_price):
        self._order_info['limit_price'] = limit_price

    @property
    def execution_details(self):
        return self._order_info['execution_details']

    @execution_details.setter
    def execution_details(self, execution_details):
        self._order_info['execution_details'] = execution_details


    def fill_less_than_or_equal_to_desired_trade(self):
        return all([x<=y for x,y in zip(self.fill, self.trade)])

    def fill_equals_zero(self):
        return all([x==0 for x in self.fill])

    def new_qty_less_than_fill(self, new_qty):
        return any([x<y for x,y in zip(new_qty, self.fill)])

    def fill_equals_desired_trade(self):
        return all([x==y for x,y in zip(self.trade, self.fill)])

    def is_zero_trade(self):
        return all([x==0 for x in self.trade])

    def same_trade_size(self, other):
        my_trade = self.trade
        other_trade = other.trade

        return all([x==y for x,y in zip(my_trade, other_trade)])

    def fill_equals_modification_quantity(self):
        if self.modification_quantity is None:
            return False
        else:
            return all([x==y for x,y in zip(self.modification_quantity, self.fill)])



class contractOrderStackData(orderStackData):
    def __repr__(self):
        return "Contract order stack: %s" % str(self._stack)

    def put_list_of_orders_on_stack(self, list_of_contract_orders, unlock_when_finished=True):
        """
        Put a list of new orders on the stack. We lock these before placing on.

        If any do not return order_id (so something has gone wrong) we remove all the relevant orders and return failure

        If all work out okay, we unlock the orders

        :param list_of_contract_orders:
        :return: list of order_ids or failure
        """
        if len(list_of_contract_orders)==0:
            return []
        log = self.log.setup(strategy_name = list_of_contract_orders[0].strategy_name,
                             instrument_code = list_of_contract_orders[0].instrument_code,
                             instrument_order_id = list_of_contract_orders[0].parent)

        list_of_child_ids = []
        status = success
        for contract_order in list_of_contract_orders:
            contract_order.lock_order()
            child_id = self.put_order_on_stack(contract_order)
            if type(child_id) is not int:
                log.warn("Failed to put contract order %s on stack error %s, rolling back entire transaction" %
                         (str(contract_order), str(child_id)),
                         contract_date = contract_order.contract_id_key)
                status = failure
                break

            else:
                list_of_child_ids.append(child_id)

        # At this point we eithier have total failure (list_of_child_ids is empty, status failure),
        #    or partial failure (list of child_ids is part filled, status failure)
        #    or total success

        if status is failure:
            # rollback the orders we added
            self.rollback_list_of_orders_on_stack(list_of_child_ids)
            return failure

        # success
        if unlock_when_finished:
            self.unlock_list_of_orders(list_of_child_ids)

        return list_of_child_ids

    def rollback_list_of_orders_on_stack(self, list_of_child_ids):
        self.log.warn("Rolling back addition of child orders %s" % str(list_of_child_ids))
        for order_id in list_of_child_ids:
            self._unlock_order_on_stack(order_id)
            self.deactivate_order(order_id)
            self.remove_order_with_id_from_stack(order_id)

        return success


    def unlock_list_of_orders(self, list_of_child_ids):
        for order_id in list_of_child_ids:
            self._unlock_order_on_stack(order_id)

        return success

def log_attributes_from_contract_order(log, contract_order):
    """
    Returns a new log object with contract_order attributes added

    :param log: logger
    :param instrument_order:
    :return: log
    """
    new_log = log.setup(
              strategy_name=contract_order.strategy_name,
              instrument_code=contract_order.instrument_code,
              contract_order_id=object_to_none(contract_order.order_id, no_order_id),
              instrument_order_id = object_to_none(contract_order.parent, no_parent, 0))


    return new_log