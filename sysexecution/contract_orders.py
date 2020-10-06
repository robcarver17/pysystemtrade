import datetime
from copy import copy

from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import (
    Order,
    tradeableObject,
    no_order_id,
    no_children,
    no_parent,
    resolve_trade_fill_fillprice,
)
from syscore.genutils import none_to_object, object_to_none
from syscore.objects import failure, success, missing_order


class contractTradeableObject(tradeableObject):
    def __init__(self, strategy_name, instrument_code, contract_id):
        """

        :param strategy_name: str
        :param instrument_code: str
        :param contract_id: a single contract_order_id YYYYMM, or a list of contract IDS YYYYMM for a spread order
        """
        if isinstance(contract_id, str):
            contract_id = list([contract_id])

        dict_def = dict(
            strategy_name=strategy_name,
            instrument_code=instrument_code,
            contract_id=contract_id,
        )
        self._set_definition(dict_def)

    @classmethod
    def from_key(instrumentTradeableObject, key):
        strategy_name, instrument_code, contract_id_str = key.split("/")
        contract_id_list = contract_id_str.split("_")

        return instrumentTradeableObject(
            strategy_name, instrument_code, contract_id_list
        )

    @property
    def contract_id(self):
        return self._definition["contract_id"]

    @property
    def contract_id_key(self):
        return "_".join(self.contract_id)

    @property
    def alt_contract_id_key(self):
        if len(self.contract_id_key) == 6:
            return self.contract_id_key + "00"

        if len(self.contract_id_key) == 8:
            return self.contract_id_key[:6]

    @property
    def strategy_name(self):
        return self._definition["strategy_name"]

    @property
    def instrument_code(self):
        return self._definition["instrument_code"]

    @property
    def key(self):
        return "/".join(
            [self.strategy_name, self.instrument_code, self.contract_id_key]
        )

    @property
    def alt_key(self):
        return "/".join([self.strategy_name,
                         self.instrument_code,
                         self.alt_contract_id_key])

    def sort_idx_for_contracts(self):
        clist = self.contract_id
        return sorted(range(len(clist)), key=lambda k: clist[k])

    def sort_contracts(self):
        clist = self.contract_id
        clist = sorted(clist)
        self._definition["contract_id"] = clist


class contractOrder(Order):
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
        algo_to_use="",
        reference_price=None,
        limit_price=None,
        filled_price=None,
        fill_datetime=None,
        generated_datetime=None,
        manual_fill=False,
        manual_trade=False,
        roll_order=False,
        inter_spread_order=False,
        calendar_spread_order=None,
        reference_of_controlling_algo=None,
        split_order=False,
        sibling_id_for_split_order=None
    ):
        """
        :param args: Either a single argument 'strategy/instrument/contract_order_id' str, or strategy, instrument, contract_order_id; followed by trade
        i.e. contractOrder(strategy, instrument, contractid, trade,  **kwargs) or 'strategy/instrument/contract_order_id', trade, type, **kwargs)

        Contract_id can either be a single str or a list of str for spread orders, all YYYYMM
        If expressed inside a longer string, separate contract str by '_'

        i.e. contractOrder('a strategy', 'an instrument', '201003', 6,  **kwargs)
         same as contractOrder('a strategy/an instrument/201003', 6,  **kwargs)
        contractOrder('a strategy', 'an instrument', ['201003', '201406'], [6,-6],  **kwargs)
          same as contractOrder('a strategy/an instrument/201003_201406', [6,-6],  **kwargs)

        :param fill: fill done so far, list of int
        :param locked: if locked an order can't be modified, bool
        :param order_id: ID given to orders once in the stack, do not use when creating order
        :param modification_status: NOT USED
        :param modification_quantity: NOT USED
        :param parent: int, order ID of parent order in upward stack
        :param children: list of int, order IDs of child orders in downward stack
        :param active: bool, inactive orders have been filled or cancelled
        :param algo_to_use: str, full pathname of method to use to execute order.
        :param reference_of_controlling_algo: str, the key of the controlling algo. If None not currently controlled.
        :param limit_price: float, limit orders only
        :param reference_price: float, used to benchmark order (usually price from previous days close)
        :param filled_price: float, used for execution calculations and p&l
        :param fill_datetime: datetime used for p&l
        :param generated_datetime: datetime order generated
        :param manual_fill: bool, fill entered manually
        :param manual_trade: bool, trade entered manually
        :param roll_order: bool, part of a (or if a spread an entire) roll order. Passive rolls will be False
        :param calendar_spread_order: bool, a calendar spread (intra-market) order
        :param inter_spread_order: bool, part of an instrument order that is a spread across multiple markets
        """

        tradeable_object, trade = self._resolve_args(args)
        self._tradeable_object = tradeable_object

        if generated_datetime is None:
            generated_datetime = datetime.datetime.now()

        (
            resolved_trade,
            resolved_fill,
            resolved_filled_price,
        ) = resolve_trade_fill_fillprice(trade, fill, filled_price)

        # ensure contracts and lists all match
        (resolved_trade,
         resolved_fill,
         resolved_filled_price,
         tradeable_object,
         ) = sort_by_cid(resolved_trade,
                         resolved_fill,
                         resolved_filled_price,
                         tradeable_object)

        if len(resolved_trade.qty) == 1:
            calendar_spread_order = False
        else:
            calendar_spread_order = True

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
        self._order_info = dict(
            algo_to_use=algo_to_use,
            reference_price=reference_price,
            limit_price=limit_price,
            manual_trade=manual_trade,
            manual_fill=manual_fill,
            roll_order=roll_order,
            calendar_spread_order=calendar_spread_order,
            inter_spread_order=inter_spread_order,
            generated_datetime=generated_datetime,
            reference_of_controlling_algo=reference_of_controlling_algo,
            split_order=split_order,
            sibling_id_for_split_order=sibling_id_for_split_order,
        )

    def _resolve_args(self, args):
        if len(args) == 2:
            tradeable_object = contractTradeableObject.from_key(args[0])
            trade = args[1]
        elif len(args) == 4:
            strategy = args[0]
            instrument = args[1]
            contract_id = args[2]
            trade = args[3]
            tradeable_object = contractTradeableObject(
                strategy, instrument, contract_id
            )
        else:
            raise Exception(
                "contractOrder(strategy, instrument, contractid, trade,  **kwargs) or ('strategy/instrument/contract_order_id', trade, **kwargs) "
            )

        return tradeable_object, trade

    def __repr__(self):
        my_repr = super().__repr__()
        if self.filled_price is not None and self.fill_datetime is not None:
            my_repr = my_repr + "Fill %s on %s" % (
                str(self.filled_price),
                str(self.fill_datetime),
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

        order = contractOrder(
            key,
            trade,
            fill=fill,
            locked=locked,
            order_id=order_id,
            modification_status=modification_status,
            modification_quantity=modification_quantity,
            parent=parent,
            children=children,
            active=active,
            fill_datetime=fill_datetime,
            filled_price=filled_price,
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
    def contract_id(self):
        return self._tradeable_object.contract_id

    @property
    def contract_id_key(self):
        return self._tradeable_object.contract_id_key

    @property
    def algo_to_use(self):
        return self._order_info["algo_to_use"]

    @algo_to_use.setter
    def algo_to_use(self, algo_to_use):
        self._order_info["algo_to_use"] = algo_to_use

    @property
    def generated_datetime(self):
        return self._order_info["reference_datetime"]

    @property
    def reference_price(self):
        return self._order_info["reference_price"]

    @reference_price.setter
    def reference_price(self, reference_price):
        self._order_info["reference_price"] = reference_price

    @property
    def limit_price(self):
        return self._order_info["limit_price"]

    @limit_price.setter
    def limit_price(self, limit_price):
        self._order_info["limit_price"] = limit_price

    @property
    def manual_trade(self):
        return self._order_info["manual_trade"]

    @property
    def manual_fill(self):
        return self._order_info["manual_fill"]

    @manual_fill.setter
    def manual_fill(self, manual_fill):
        self._order_info["manual_fill"] = manual_fill

    @property
    def is_split_order(self):
        return self._order_info["split_order"]

    def split_order(self, sibling_order_id):
        self._order_info["split_order"] = True
        self._order_info["sibling_id_for_split_order"] = sibling_order_id

    @property
    def roll_order(self):
        return self._order_info["roll_order"]

    @property
    def calendar_spread_order(self):
        return self._order_info["calendar_spread_order"]

    @property
    def reference_of_controlling_algo(self):
        return self._order_info["reference_of_controlling_algo"]

    def is_order_controlled_by_algo(self):
        return self._order_info["reference_of_controlling_algo"] is not None

    def add_controlling_algo_ref(self, control_algo_ref):
        if self.reference_of_controlling_algo == control_algo_ref:
            # irrelevant, already controlled
            return success
        if self.is_order_controlled_by_algo():
            raise Exception(
                "Already controlled by %s" % self.reference_of_controlling_algo
            )
        self._order_info["reference_of_controlling_algo"] = control_algo_ref

        return success

    def release_order_from_algo_control(self):
        self._order_info["reference_of_controlling_algo"] = None

    @property
    def inter_spread_order(self):
        return self._order_info["inter_spread_order"]

    def log_with_attributes(self, log):
        """
        Returns a new log object with contract_order attributes added

        :param log: logger
        :return: log
        """
        new_log = log.setup(
            strategy_name=self.strategy_name,
            instrument_code=self.instrument_code,
            contract_order_id=object_to_none(self.order_id, no_order_id),
            instrument_order_id=object_to_none(self.parent, no_parent, 0),
        )

        return new_log

    def split_spread_order(self):
        """

        :param self:
        :return: list of contract orders, will be original order if not a spread order
        """
        if len(self.contract_id) == 1:
            # not a spread trade
            return [self]

        list_of_derived_contract_orders = []
        original_as_dict = self.as_dict()
        for contractid, trade_qty, fill, fill_price in zip(
            self.contract_id, self.trade, self.fill, self.filled_price
        ):

            new_order_as_dict = copy(original_as_dict)
            new_tradeable_object = contractTradeableObject(
                self.strategy_name, self.instrument_code, contractid
            )
            new_key = new_tradeable_object.key

            new_order_as_dict["key"] = new_key
            new_order_as_dict["trade"] = trade_qty
            new_order_as_dict["fill"] = fill
            new_order_as_dict["filled_price"] = fill_price
            new_order_as_dict["order_id"] = no_order_id

            new_order = contractOrder.from_dict(new_order_as_dict)
            new_order.split_order(self.order_id)

            list_of_derived_contract_orders.append(new_order)

        return list_of_derived_contract_orders


def sort_by_cid(
        resolved_trade,
        resolved_fill,
        resolved_filled_price,
        tradeable_object):
    sort_order = tradeable_object.sort_idx_for_contracts()
    resolved_trade.sort_with_idx(sort_order)
    resolved_fill.sort_with_idx(sort_order)
    resolved_filled_price.sort_with_idx(sort_order)

    tradeable_object.sort_contracts()

    return resolved_trade, resolved_fill, resolved_filled_price, tradeable_object


class contractOrderStackData(orderStackData):
    def __repr__(self):
        return "Contract order stack: %s" % str(self._stack)

    def manual_fill_for_order_id(
        self, order_id, fill_qty, filled_price=None, fill_datetime=None
    ):
        result = self.change_fill_quantity_for_order(
            order_id, fill_qty, filled_price=filled_price, fill_datetime=fill_datetime)
        if result is failure:
            return failure

        # all good need to show it was a manual fill
        order = self.get_order_with_id_from_stack(order_id)
        order.manual_fill = True
        result = self._change_order_on_stack(order_id, order)

        return result

    def add_controlling_algo_ref(self, order_id, control_algo_ref):
        """

        :param order_id: int
        :param control_algo_ref: str or None
        :return:
        """
        if control_algo_ref is None:
            return self.release_order_from_algo_control(order_id)

        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            raise Exception(
                "Can't add controlling ago as order %d doesn't exist" %
                order_id)

        try:
            modified_order = copy(existing_order)
            modified_order.add_controlling_algo_ref(control_algo_ref)
        except Exception as e:
            raise Exception(
                "%s couldn't add controlling algo %s to order %d"
                % (str(e), control_algo_ref, order_id)
            )

        result = self._change_order_on_stack(order_id, modified_order)

        if result is not success:
            raise Exception(
                "%s when trying to add controlling algo to order %d"
                % (str(result), order_id)
            )

        return success

    def release_order_from_algo_control(self, order_id):
        existing_order = self.get_order_with_id_from_stack(order_id)
        if existing_order is missing_order:
            raise Exception(
                "Can't release controlling ago as order %d doesn't exist" %
                order_id)

        if not existing_order.is_order_controlled_by_algo():
            # No change required
            return success

        try:
            modified_order = copy(existing_order)
            modified_order.release_order_from_algo_control()
        except Exception as e:
            raise Exception(
                "%s couldn't release controlling algo for order %d" %
                (str(e), order_id))

        result = self._change_order_on_stack(order_id, modified_order)

        if result is not success:
            raise Exception(
                "%s when trying to add controlling algo to order %d"
                % (str(result), order_id)
            )

        return success
