import datetime
from copy import copy

from sysexecution.orders.base_orders import (
    Order,
    no_order_id,
    no_children,
    no_parent,
    resolve_inputs_to_order, orderType)

from sysexecution.trade_qty import tradeQuantity
from sysexecution.fill_price import fillPrice
from sysexecution.orders.list_of_orders import listOfOrders
from sysobjects.production.tradeable_object import futuresContractStrategy, instrumentStrategy
from sysobjects.contract_dates_and_expiries import singleContractDate
from syscore.genutils import none_to_object, object_to_none
from syscore.objects import success



class contractOrderType(orderType):
    def allowed_types(self):
        return ['best', 'market', 'limit', 'balance_trade']

best_order_type  = contractOrderType('best')
balance_order_type = contractOrderType('balance')


class contractOrder(Order):
    def __init__(
        self,
        *args,
        fill: tradeQuantity = None,
        filled_price: fillPrice = None,
        fill_datetime: datetime.datetime = None,
        locked=False,
        order_id: int = no_order_id,
        parent: int = no_parent,
        children: list = no_children,
        active: bool = True,
        order_type: contractOrderType = contractOrderType("best"),

        limit_price: float =None,
        reference_price: float=None,
        generated_datetime: datetime.datetime=None,

        manual_fill:bool =False,
        manual_trade: bool=False,
        roll_order: bool=False,
        inter_spread_order: bool=False,

        algo_to_use: str="",
        reference_of_controlling_algo: str=None,

        split_order: bool=False,
        sibling_id_for_split_order: int=None,
        **kwargs
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

        tradeable_object, trade = resolve_contract_order_args(args)

        if generated_datetime is None:
            generated_datetime = datetime.datetime.now()

        (
            resolved_trade,
            resolved_fill,
            resolved_filled_price,
        ) = resolve_inputs_to_order(trade, fill, filled_price)

        # ensure contracts and lists all match
        (resolved_trade,
         resolved_fill,
         resolved_filled_price,
         tradeable_object,
         ) = sort_inputs_by_contract_date_order(resolved_trade,
                                                resolved_fill,
                                                resolved_filled_price,
                                                tradeable_object)

        if len(resolved_trade) == 1:
            calendar_spread_order = False
        else:
            calendar_spread_order = True

        order_info = dict(
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
            sibling_id_for_split_order=sibling_id_for_split_order
        )

        super().__init__(tradeable_object,
                        trade= resolved_trade,
                        fill = resolved_fill,
                        filled_price= resolved_filled_price,
                        fill_datetime = fill_datetime,
                        locked = locked,
                        order_id=order_id,
                        parent = parent,
                        children= children,
                        active=active,
                        order_type=order_type,
                        **order_info
                        )



    @classmethod
    def from_dict(contractOrder, order_as_dict):
        trade = order_as_dict.pop("trade")
        key = order_as_dict.pop("key")
        fill = order_as_dict.pop("fill")
        filled_price = order_as_dict.pop("filled_price")
        fill_datetime = order_as_dict.pop("fill_datetime")

        locked = order_as_dict.pop("locked")
        order_id = none_to_object(order_as_dict.pop("order_id"), no_order_id)
        parent = none_to_object(order_as_dict.pop("parent"), no_parent)
        children = none_to_object(order_as_dict.pop("children"), no_children)
        active = order_as_dict.pop("active")
        order_type = contractOrderType(order_as_dict.pop("order_type"))

        order_info = order_as_dict

        order = contractOrder(
            key,
            trade,
            fill=fill,
            locked=locked,
            order_id=order_id,
            parent=parent,
            children=children,
            active=active,
            fill_datetime=fill_datetime,
            filled_price=filled_price,
            order_type = order_type,
            **order_info
        )

        return order

    @property
    def strategy_name(self):
        return self.tradeable_object.strategy_name

    @property
    def instrument_code(self):
        return self.tradeable_object.instrument_code

    @property
    def contract_date(self):
        return self.tradeable_object.contract_date

    @property
    def contract_date_key(self):
        return self.tradeable_object.contract_date_key

    @property
    def futures_contract(self):
        return self.tradeable_object.futures_contract

    @property
    def instrument_strategy(self) -> instrumentStrategy:
        return self.tradeable_object.instrument_strategy

    @property
    def algo_to_use(self):
        return self.order_info["algo_to_use"]

    @algo_to_use.setter
    def algo_to_use(self, algo_to_use):
        self.order_info["algo_to_use"] = algo_to_use

    @property
    def generated_datetime(self):
        return self.order_info["reference_datetime"]

    @property
    def reference_price(self):
        return self.order_info["reference_price"]

    @reference_price.setter
    def reference_price(self, reference_price):
        self.order_info["reference_price"] = reference_price

    @property
    def limit_price(self):
        return self.order_info["limit_price"]

    @limit_price.setter
    def limit_price(self, limit_price):
        self.order_info["limit_price"] = limit_price

    @property
    def manual_trade(self):
        return self.order_info["manual_trade"]

    @property
    def manual_fill(self):
        return self.order_info["manual_fill"]

    @manual_fill.setter
    def manual_fill(self, manual_fill):
        self.order_info["manual_fill"] = manual_fill

    @property
    def is_split_order(self):
        return self.order_info["split_order"]

    def split_order(self, sibling_order_id):
        self.order_info["split_order"] = True
        self.order_info["sibling_id_for_split_order"] = sibling_order_id

    @property
    def roll_order(self):
        return self.order_info["roll_order"]

    @property
    def calendar_spread_order(self):
        return self.order_info["calendar_spread_order"]

    @property
    def reference_of_controlling_algo(self):
        return self.order_info["reference_of_controlling_algo"]

    def is_order_controlled_by_algo(self):
        return self.order_info["reference_of_controlling_algo"] is not None

    def add_controlling_algo_ref(self, control_algo_ref):
        if self.reference_of_controlling_algo == control_algo_ref:
            # irrelevant, already controlled
            return success
        if self.is_order_controlled_by_algo():
            raise Exception(
                "Already controlled by %s" % self.reference_of_controlling_algo
            )
        self.order_info["reference_of_controlling_algo"] = control_algo_ref

        return success

    def release_order_from_algo_control(self):
        self.order_info["reference_of_controlling_algo"] = None

    @property
    def inter_spread_order(self):
        return self.order_info["inter_spread_order"]

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

    def split_spread_order(self) -> listOfOrders:
        """

        :param self:
        :return: list of contract orders, will be original order if not a spread order
        """
        if len(self.contract_date) == 1:
            # not a spread trade
            return listOfOrders([self])

        list_of_derived_contract_orders = []

        for contractid, trade_qty, fill, fill_price in zip(
            self.contract_date, self.trade, self.fill, self.filled_price
        ):
            new_order = create_split_contract_order(original_order=self,
                                                    contractid=contractid,
                                                    trade_qty=trade_qty,
                                                    fill=fill,
                                                    fill_price = fill_price)

            list_of_derived_contract_orders.append(new_order)

        return listOfOrders(list_of_derived_contract_orders)

def create_split_contract_order(original_order: contractOrder,
                                contractid: singleContractDate,
                                trade_qty: int,
                                fill: int,
                                fill_price: float) -> contractOrder:

    new_order_as_dict = create_split_contract_order_dict(original_order=original_order,
                                                contractid=contractid,
                                                trade_qty=trade_qty,
                                                fill=fill,
                                                fill_price=fill_price)

    new_order = contractOrder.from_dict(new_order_as_dict)
    new_order.split_order(original_order.order_id)

    return new_order


def create_split_contract_order_dict(original_order: contractOrder,
                                contractid: singleContractDate,
                                trade_qty: int,
                                fill: int,
                                fill_price: float) -> dict:


    original_as_dict = original_order.as_dict()
    new_order_as_dict = copy(original_as_dict)
    new_tradeable_object = futuresContractStrategy(
        original_order.strategy_name, original_order.instrument_code, contractid
    )
    new_key = new_tradeable_object.key

    new_order_as_dict["key"] = new_key
    new_order_as_dict["trade"] = trade_qty
    new_order_as_dict["fill"] = fill
    new_order_as_dict["filled_price"] = fill_price
    new_order_as_dict["order_id"] = no_order_id

    return new_order_as_dict

def resolve_contract_order_args(args: list) -> (futuresContractStrategy, tradeQuantity):
    if len(args) == 2:
        tradeable_object = futuresContractStrategy.from_key(args[0])
        trade = args[1]
    elif len(args) == 4:
        strategy = args[0]
        instrument = args[1]
        contract_id = args[2]
        trade = args[3]
        tradeable_object = futuresContractStrategy(
            strategy, instrument, contract_id
        )
    else:
        raise Exception(
            "contractOrder(strategy, instrument, contractid, trade,  **kwargs) or ('strategy/instrument/contract_order_id', trade, **kwargs) "
        )

    return tradeable_object, trade

def sort_inputs_by_contract_date_order(
        resolved_trade: tradeQuantity,
        resolved_fill: tradeQuantity,
        resolved_filled_price: fillPrice,
        tradeable_object: futuresContractStrategy):

    sort_order = tradeable_object.sort_idx_for_contracts()
    resolved_trade.sort_with_idx(sort_order)
    resolved_fill.sort_with_idx(sort_order)
    resolved_filled_price.sort_with_idx(sort_order)

    tradeable_object.sort_contracts_with_idx(sort_order)

    return resolved_trade, resolved_fill, resolved_filled_price, tradeable_object


