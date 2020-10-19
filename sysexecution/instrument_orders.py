import datetime

from syscore.genutils import none_to_object, object_to_none
from syscore.objects import missing_order, success, zero_order

from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import (
    Order,
    tradeableObject,
    resolve_trade_fill_fillprice,
    no_order_id,
    no_children,
    no_parent,
)

possible_order_types = [
    "best",
    "market",
    "limit",
    "Zero-roll-order",
    "balance_trade"]


class instrumentTradeableObject(tradeableObject):
    def __init__(self, strategy_name, instrument_code):
        dict_def = dict(
            strategy_name=strategy_name,
            instrument_code=instrument_code)
        self._set_definition(dict_def)

    @classmethod
    def from_key(instrumentTradeableObject, key):
        strategy_name, instrument_code = key.split("/")

        return instrumentTradeableObject(strategy_name, instrument_code)

    @property
    def strategy_name(self):
        return self._definition["strategy_name"]

    @property
    def instrument_code(self):
        return self._definition["instrument_code"]

    @property
    def key(self):
        return "/".join([self._definition["strategy_name"],
                         self._definition["instrument_code"]])


class instrumentOrder(Order):
    def __init__(
        self,
        *args,
        fill=None,
        locked=False,
        order_id=no_order_id,
        modification_status=None,
        modification_quantity=None,
        parent=no_parent,
        children=no_children,
        active=True,
        order_type="best",
        limit_price=None,
        limit_contract=None,
        reference_datetime=None,
        reference_price=None,
        reference_contract=None,
        generated_datetime=None,
        filled_price=None,
        fill_datetime=None,
        manual_trade=False,
        roll_order=False
    ):
        """

        :param args: Either a single argument 'strategy/instrument' str, or strategy, instrument; followed by trade
        i.e. instrumentOrder(strategy, instrument, trade,  **kwargs) or 'strategy/instrument', trade, type, **kwargs)

        :param fill: fill done so far, int
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param modification_status: NOT USED
        :param modification_quantity: NOT USED
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
        :param args: Either 2: strategy, instrument; or 1: instrumentTradeableObject
        :param type: str
        """
        if len(args) == 2:
            self._tradeable_object = instrumentTradeableObject.from_key(
                args[0])
            trade = args[1]
        else:
            strategy = args[0]
            instrument = args[1]
            trade = args[2]
            self._tradeable_object = instrumentTradeableObject(
                strategy, instrument)

        if generated_datetime is None:
            generated_datetime = datetime.datetime.now()

        (
            resolved_trade,
            resolved_fill,
            resolved_filled_price,
        ) = resolve_trade_fill_fillprice(trade, fill, filled_price)

        self._trade = resolved_trade
        self._fill = resolved_fill
        self._filled_price = resolved_filled_price
        self._fill_datetime = fill_datetime
        self._locked = locked
        self._order_id = order_id
        self._modification_status = modification_status
        self._modification_quantity = modification_quantity
        self._parent = parent
        self._children = children
        self._active = active

        assert order_type in possible_order_types
        self._order_info = dict(
            order_type=order_type,
            limit_contract=limit_contract,
            limit_price=limit_price,
            reference_contract=reference_contract,
            reference_price=reference_price,
            manual_trade=manual_trade,
            roll_order=roll_order,
            reference_datetime=reference_datetime,
            generated_datetime=generated_datetime,
        )

    def __repr__(self):
        my_repr = super().__repr__()
        if self.filled_price is not None and self.fill_datetime is not None:
            my_repr = my_repr + "Fill %s on %s" % (
                str(self.filled_price),
                self.fill_datetime,
            )
        my_repr = my_repr + " %s" % str(self._order_info)

        return my_repr

    def terse_repr(self):
        order_repr = super().__repr__()
        return order_repr

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
        trade = order_as_dict.pop("trade")
        key = order_as_dict.pop("key")
        fill = order_as_dict.pop("fill")
        filled_price = order_as_dict.pop("filled_price")
        fill_datetime = order_as_dict.pop("fill_datetime")
        locked = order_as_dict.pop("locked")
        order_id = none_to_object(order_as_dict.pop("order_id"), no_order_id)
        modification_status = order_as_dict.pop("modification_status")
        modification_quantity = order_as_dict.pop("modification_quantity")
        parent = none_to_object(order_as_dict.pop("parent"), no_parent)
        children = none_to_object(order_as_dict.pop("children"), no_children)
        active = order_as_dict.pop("active")

        order_info = order_as_dict

        order = instrumentOrder(
            key,
            trade,
            fill=fill,
            locked=locked,
            order_id=order_id,
            modification_status=modification_status,
            modification_quantity=modification_quantity,
            parent=parent,
            children=children,
            fill_datetime=fill_datetime,
            filled_price=filled_price,
            active=active,
            **order_info
        )

        return order

    @property
    def strategy_name(self):
        return self._tradeable_object.strategy_name

    @property
    def instrument_code(self):
        return self._tradeable_object.instrument_code

    @property
    def order_type(self):
        return self._order_info["order_type"]

    @order_type.setter
    def order_type(self, order_type):
        self._order_info["order_type"] = order_type

    @property
    def limit_contract(self):
        return self._order_info["limit_contract"]

    @limit_contract.setter
    def limit_contract(self, limit_contract):
        self._order_info["limit_contract"] = limit_contract

    @property
    def limit_price(self):
        return self._order_info["limit_price"]

    @limit_price.setter
    def limit_price(self, limit_price):
        self._order_info["limit_price"] = limit_price

    @property
    def reference_contract(self):
        return self._order_info["reference_contract"]

    @reference_contract.setter
    def reference_contract(self, reference_contract):
        self._order_info["reference_contract"] = reference_contract

    @property
    def reference_price(self):
        return self._order_info["reference_price"]

    @reference_price.setter
    def reference_price(self, reference_price):
        self._order_info["reference_price"] = reference_price

    @property
    def reference_datetime(self):
        return self._order_info["reference_datetime"]

    @property
    def generated_datetime(self):
        return self._order_info["reference_datetime"]

    @property
    def manual_trade(self):
        return self._order_info["manual_trade"]

    @property
    def roll_order(self):
        return self._order_info["roll_order"]

    def log_with_attributes(self, log):
        """
        Returns a new log object with instrument_order attributes added

        :param log: logger
        :return: log
        """
        new_log = log.setup(
            strategy_name=self.strategy_name,
            instrument_code=self.instrument_code,
            instrument_order_id=object_to_none(self.order_id, no_order_id),
        )

        return new_log


class instrumentOrderStackData(orderStackData):
    def __repr__(self):
        return "Instrument order stack: %s" % str(self._stack)

    def put_manual_order_on_stack(self, new_order):
        """
        Puts an order on the stack ignoring the usual checks

        :param new_order:
        :return: order_id or failure object
        """

        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            new_order)

        return order_id_or_error

    def put_order_on_stack(self, new_order, allow_zero_orders=False):
        """
        Put an order on the stack, or at least try to:
        - if no existing order for this instrument/strategy, add
        - if an existing order for this instrument/strategy, put an adjusting order on

        :param new_order: Order
        :return: order_id or failure condition: duplicate_order, failure
        """

        existing_order_id_list = self._get_order_with_same_tradeable_object_on_stack(
            new_order)
        if existing_order_id_list is missing_order:
            result = self._put_new_order_on_stack_when_no_existing_order(
                new_order, allow_zero_orders=allow_zero_orders
            )
        else:
            result = self._put_adjusting_order_on_stack(
                new_order, existing_order_id_list, allow_zero_orders=allow_zero_orders)
        return result

    def does_strategy_and_instrument_already_have_order_on_stack(
        self, strategy_name, instrument_code
    ):
        pseudo_order = instrumentOrder(strategy_name, instrument_code, 0)
        existing_orders = self._get_order_with_same_tradeable_object_on_stack(
            pseudo_order
        )
        if existing_orders is missing_order:
            return False
        return True

    def _put_new_order_on_stack_when_no_existing_order(
        self, new_order, allow_zero_orders=False
    ):
        log = new_order.log_with_attributes(self.log)

        if new_order.is_zero_trade() and not allow_zero_orders:
            log.msg("Zero orders not allowed")
            return zero_order

        # no current order for this instrument/strategy
        log.msg(
            "New order %s putting on %s" %
            (str(new_order), self.__repr__()))
        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            new_order)
        return order_id_or_error

    def _put_adjusting_order_on_stack(
        self, new_order, existing_order_id_list, allow_zero_orders=False
    ):
        """
        Considering the unfilled orders already on the stack place an additional adjusting order

        :param new_order:
        :return:
        """
        log = new_order.log_with_attributes(self.log)

        existing_orders = [
            self.get_order_with_id_from_stack(order_id)
            for order_id in existing_order_id_list
        ]
        existing_trades = [
            existing_order.trade for existing_order in existing_orders]
        existing_fills = [
            existing_order.fill for existing_order in existing_orders]

        net_existing_trades = sum(existing_trades)
        net_existing_fills = sum(existing_fills)
        net_existing_trades_to_execute = net_existing_trades - net_existing_fills

        new_trade = new_order.trade

        # can change sign
        residual_trade = new_trade - net_existing_trades_to_execute
        adjusted_order = new_order.replace_trade_only_use_for_unsubmitted_trades(
            residual_trade)

        if adjusted_order.is_zero_trade() and not allow_zero_orders:
            # Trade we want is already in the system
            return zero_order

        log.msg(
            "Already have orders %s wanted %s so putting on order for %s (%s)"
            % (
                str(existing_trades),
                str(new_trade),
                str(residual_trade),
                str(adjusted_order),
            )
        )
        order_id_or_error = self._put_order_on_stack_and_get_order_id(
            adjusted_order)

        return order_id_or_error

