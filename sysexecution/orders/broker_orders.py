from enum import Enum
from copy import copy
import datetime

from sysexecution.orders.base_orders import (
    no_order_id,
    no_children,
    no_parent,
    resolve_inputs_to_order, orderType)
from sysexecution.orders.base_orders import Order
from sysexecution.trade_qty import tradeQuantity
from sysexecution.fill_price import fillPrice
from sysexecution.price_quotes import quotePrice
from sysexecution.orders.contract_orders import contractOrder, resolve_contract_order_args
from sysexecution.orders.instrument_orders import instrumentOrder
from sysobjects.production.tradeable_object import futuresContractStrategy, instrumentStrategy, futuresContract
from sysobjects.contract_dates_and_expiries import singleContractDate

from syscore.genutils import none_to_object, object_to_none
from syscore.objects import fill_exceeds_trade, success


class brokerOrderType(orderType):
    def allowed_types(self):
        return ['market', 'limit']

market_order_type = brokerOrderType('market')
limit_order_type = brokerOrderType('limit')

class brokerOrder(Order):
    def __init__(
        self,
        *args,
        fill: tradeQuantity=None,
            filled_price: fillPrice = None,
            fill_datetime: datetime.datetime = None,
        locked: bool=False,
        order_id: int=no_order_id,
        parent: int=no_parent,
        children: list=no_children,
        active: bool=True,
        order_type: brokerOrderType = brokerOrderType("market"),

        algo_used: str="",
        algo_comment: str="",

        limit_price: float=None,
        submit_datetime: datetime.datetime=None,
        side_price: quotePrice=None,
        mid_price: quotePrice=None,

        roll_order: bool = False,

        broker: str="",
        broker_account: str="",
        broker_clientid: str="",
        broker_permid: str = "",
        broker_tempid: str = "",
        broker_objects=dict(),

        commission: float=0.0,
        manual_fill: bool=False,

        split_order: bool=False,
        sibling_id_for_split_order=None,
        **kwargs_ignored
    ):
        """

        :param args: Either a single argument 'strategy/instrument/contract_id' str, or strategy, instrument, contract_id; followed by trade
        i.e. brokerOrder(strategy, instrument, contractid, trade,  **kwargs) or 'strategy/instrument/contract_id', trade, type, **kwargs)

        Contract_id can either be a single str or a list of str for spread orders, all YYYYMM
        If expressed inside a longer string, separate contract str by '_'

        i.e. brokerOrder('a strategy', 'an instrument', '201003', 6,  **kwargs)
         same as brokerOrder('a strategy/an instrument/201003', 6,  **kwargs)
        brokerOrder('a strategy', 'an instrument', ['201003', '201406'], [6,-6],  **kwargs)
          same as brokerOrder('a strategy/an instrument/201003_201406', [6,-6],  **kwargs)
        :param fill:  fill done so far, list of int
        :param locked: bool, is order locked
        :param order_id: int, my ref number
        :param modification_status: NOT USED
        :param modification_quantity: NOT USED
        :param parent: int or not supplied, parent order
        :param children: list of int or not supplied, child order ids (FUNCTIONALITY NOT USED HERE)
        :param active: bool, is order active or has been filled/cancelled
        :param algo_used: Name of the algo I used to generate the order
        :param order_type: market or limit order (other types may be supported in future)
        :param limit_price: if relevant, float
        :param filled_price: float
        :param submit_datetime: datetime
        :param fill_datetime: datetime
        :param side_price: Price on the 'side' we are submitting eg offer if buying, when order submitted
        :param mid_price: Average of bid and offer when we are submitting
        :param algo_comment: Any comment made by the algo, eg 'Aggressive', 'Passive'...
        :param broker: str, name of broker
        :param broker_account: str, brokerage account
        :param broker_clientid: int, client ID used to generate order
        :param commission: float
        :param broker_permid: Brokers permanent ref number
        :param broker_tempid: Brokers temporary ref number
        :param broker_objects: store brokers representation of objects
        :param manual_fill: bool, was fill entered manually rather than being picked up from IB

        """

        tradeable_object, trade = resolve_contract_order_args(args)

        if len(trade) == 1:
            calendar_spread_order = False
        else:
            calendar_spread_order = True

        order_info = dict(
            algo_used=algo_used,
            submit_datetime=submit_datetime,
            limit_price=limit_price,
            manual_fill=manual_fill,
            calendar_spread_order=calendar_spread_order,
            side_price=side_price,
            mid_price=mid_price,
            algo_comment=algo_comment,
            broker=broker,
            broker_account=broker_account,
            broker_permid=broker_permid,
            broker_tempid=broker_tempid,
            broker_clientid=broker_clientid,
            commission=commission,
            split_order=split_order,
            sibling_id_for_split_order=sibling_id_for_split_order,
            roll_order=roll_order
        )

        super().__init__(tradeable_object,
                        trade= trade,
                        fill = fill,
                        filled_price= filled_price,
                        fill_datetime = fill_datetime,
                        locked = locked,
                        order_id=order_id,
                        parent = parent,
                        children= children,
                        active=active,
                        order_type=order_type,
                        **order_info
                        )

        # NOTE: we do not include these in the normal order info dict
        # This means they will NOT be saved when we do .as_dict(), i.e. they won't be saved in the mongo record
        # This is deliberate since these objects can't be saved accordingly
        # Instead we store them only in a single session to make it easier to
        # match and modify orders

        self._broker_objects = broker_objects

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
    def instrument_strategy(self) -> instrumentStrategy:
        return self.tradeable_object.instrument_strategy

    @property
    def contract_date_key(self):
        return self.tradeable_object.contract_date_key

    @property
    def limit_price(self):
        return self.order_info["limit_price"]

    @limit_price.setter
    def limit_price(self, limit_price):
        self.order_info["limit_price"] = limit_price



    @property
    def algo_used(self):
        return self.order_info["algo_used"]

    @property
    def broker_objects(self):
        return self._broker_objects


    @property
    def calendar_spread_order(self):
        return self.order_info["calendar_spread_order"]


    @property
    def submit_datetime(self):
        return self.order_info["submit_datetime"]

    @submit_datetime.setter
    def submit_datetime(self, submit_datetime):
        self.order_info["submit_datetime"] = submit_datetime

    @property
    def manual_fill(self):
        return self.order_info["manual_fill"]

    @manual_fill.setter
    def manual_fill(self, manual_fill):
        self.order_info["manual_fill"] = manual_fill

    @property
    def side_price(self):
        return self.order_info["side_price"]

    @property
    def mid_price(self):
        return self.order_info["mid_price"]

    @property
    def algo_comment(self):
        return self.order_info["algo_comment"]

    @algo_comment.setter
    def algo_comment(self, comment):
        self.order_info["algo_comment"] = comment

    @property
    def broker(self):
        return self.order_info["broker"]

    @property
    def broker_account(self):
        return self.order_info["broker_account"]

    @property
    def broker_permid(self):
        return self.order_info["broker_permid"]

    @broker_permid.setter
    def broker_permid(self, permid):
        self.order_info["broker_permid"] = permid

    @property
    def broker_clientid(self):
        return self.order_info["broker_clientid"]

    @broker_clientid.setter
    def broker_clientid(self, broker_clientid):
        self.order_info["broker_clientid"] = broker_clientid

    @property
    def broker_tempid(self):
        return self.order_info["broker_tempid"]

    @broker_tempid.setter
    def broker_tempid(self, broker_tempid):
        self.order_info["broker_tempid"] = broker_tempid

    @property
    def commission(self):
        return self.order_info["commission"]

    @commission.setter
    def commission(self, comm):
        self.order_info["commission"] = comm

    @property
    def futures_contract(self):
        return futuresContract(instrument_object=self.instrument_code, contract_date_object=self.contract_date)

    @classmethod
    def from_dict(instrumentOrder, order_as_dict):
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
        order_type = brokerOrderType(order_as_dict.pop("order_type"))

        order_info = order_as_dict

        order = brokerOrder(
            key,
            trade,
            fill=fill,
            locked=locked,
            order_id=order_id,
            parent=parent,
            children=children,
            active=active,
            filled_price=filled_price,
            fill_datetime=fill_datetime,
            order_type=order_type,
            **order_info
        )

        return order


    def log_with_attributes(self, log):
        """
        Returns a new log object with broker_order attributes added

        :param log: logger
        :return: log
        """
        broker_order = self
        new_log = log.setup(
            strategy_name=broker_order.strategy_name,
            instrument_code=broker_order.instrument_code,
            contract_order_id=object_to_none(broker_order.parent, no_parent),
            broker_order_id=object_to_none(broker_order.order_id, no_order_id),
        )

        return new_log

    def add_execution_details_from_matched_broker_order(
            self, matched_broker_order):
        fill_qty_okay = self.trade.fill_less_than_or_equal_to_desired_trade(
            matched_broker_order.fill
        )
        if not fill_qty_okay:
            return fill_exceeds_trade
        self.fill_order(
            matched_broker_order.fill,
            filled_price=matched_broker_order.filled_price,
            fill_datetime=matched_broker_order.fill_datetime,
        )
        self.commission = matched_broker_order.commission
        self.broker_permid = matched_broker_order.broker_permid
        self.algo_comment = matched_broker_order.algo_comment

        return success


    @property
    def is_split_order(self):
        return self.order_info["split_order"]

    def split_order(self, sibling_order_id):
        self.order_info["split_order"] = True
        self.order_info["sibling_id_for_split_order"] = sibling_order_id

    def split_spread_order(self):
        """

        :param self:
        :return: list of contract orders, will be original order if not a spread order
        """
        if len(self.contract_date) == 1:
            # not a spread trade
            return [self]

        list_of_derived_broker_orders = []
        original_as_dict = self.as_dict()
        for contractid, trade_qty, fill, fill_price, mid_price, side_price in zip(
            self.contract_date,
            self.trade,
            self.fill,
            self.filled_price,
            self.mid_price,
            self.side_price,
        ):

            new_order = create_split_broker_order(original_order=original_as_dict,
                                                  contractid=contractid,
                                                  fill=fill,
                                                  fill_price=fill_price,
                                                  mid_price=mid_price,
                                                  side_price=side_price,
                                                  trade_qty=trade_qty)

            list_of_derived_broker_orders.append(new_order)

        return list_of_derived_broker_orders

def create_split_broker_order(original_order: brokerOrder,
                                contractid: singleContractDate,
                                trade_qty: int,
                                fill: int,
                                fill_price: float,
                              mid_price: float,
                              side_price: float) -> brokerOrder:

    new_order_as_dict = create_split_broker_order_dict(original_order=original_order,
                                                       contractid=contractid,
                                                       fill=fill,
                                                       fill_price=fill_price,
                                                       mid_price=mid_price,
                                                       side_price=side_price,
                                                       trade_qty=trade_qty

                                                       )
    new_order = brokerOrder.from_dict(new_order_as_dict)
    new_order.split_order(original_order.order_id)

    return new_order

def create_split_broker_order_dict(original_order: brokerOrder,
                                contractid: singleContractDate,
                                trade_qty: int,
                                fill: int,
                                fill_price: float,
                              mid_price: float,
                              side_price: float) -> dict:

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
    new_order_as_dict["mid_price"] = mid_price
    new_order_as_dict["side_price"] = side_price

    return new_order_as_dict


def create_new_broker_order_from_contract_order(
    contract_order: contractOrder,
    order_type: brokerOrderType=brokerOrderType('market'),
    limit_price: float=None,
    submit_datetime: datetime.datetime=None,
    side_price: quotePrice=None,
    mid_price: quotePrice=None,
    algo_comment: str="",
    broker: str="",
    broker_account: str="",
    broker_clientid: str="",
    broker_permid: str="",
    broker_tempid: str="",
) -> brokerOrder:

    if submit_datetime is None:
        submit_datetime = datetime.datetime.now()

    broker_order = brokerOrder(
        contract_order.key,
        contract_order.trade,
        parent=contract_order.order_id,
        algo_used=contract_order.algo_to_use,
        order_type=order_type,
        limit_price=limit_price,
        side_price=side_price,
        mid_price=mid_price,
        broker=broker,
        broker_account=broker_account,
        broker_clientid=broker_clientid,
        submit_datetime=submit_datetime,
        algo_comment=algo_comment,
        broker_permid=broker_permid,
        broker_tempid=broker_tempid,
        roll_order=contract_order.roll_order,
        manual_fill=contract_order.manual_fill

    )

    return broker_order

## Not very pretty but only used for diagnostic TCA
class brokerOrderWithParentInformation(brokerOrder):
    @classmethod
    def create_augemented_order(self, order: brokerOrder, instrument_order: instrumentOrder, contract_order: contractOrder):

        # Price when the trade was generated. We use the contract order price since
        #  the instrument order price may refer to a different contract
        reference_price = contract_order.reference_price

        # when the trade was originally generated, this is the instrument order
        # used to measure effects of delay eg from close
        generated_datetime = instrument_order.generated_datetime

        # instrument order prices may refer to a different contract
        # so we use the contract order limit
        parent_limit = contract_order.limit_price



        if order.is_split_order:
            # Note; multiple leg orders are 'split' before adding to the database
            #  The original order is then zeroed out
            #  This means there aren't any spread broker orders in the database
            # WHAT HAPPENS WITH A TWO LEVEL SPLIT?
            # FIXME THIS WHOLE THING NEEDS A LOT OF CAREFUL THOUGHT

            # We won't use these, and it may cause bugs for orders saved with

            ## A few possible cases:
            # - The instrument order is a non spread single leg and so is the contract (and broker) legs
            #          This is easy.
            # - The instrument order is a non spread flat trade calendar spread roll trade, and so are the contract/broker legs
            #          Here there is no reference price or limit price
            #          The b
            # -  The instrument order is a spread trade (calendar spread)
            #          Here the reference (and possibly limit prices) will be for the spread
            #          For the split order

            calc_mid = None
            calc_side = None
            calc_fill = None
        else:
            # If it isn't a split order then it must be a single leg trade
            calc_mid = order.trade.get_spread_price(order.mid_price)
            calc_side = order.trade.get_spread_price(order.side_price)
            calc_fill = order.trade.get_spread_price(order.filled_price)


        order.parent_reference_price = reference_price
        order.parent_generated_datetime = generated_datetime
        order.parent_limit_price = parent_limit

        order.calculated_filled_price = calc_fill
        order.calculated_mid_price = calc_mid
        order.calculated_side_price = calc_side

        order.buy_or_sell = order.trade.buy_or_sell()

        return brokerOrderWithParentInformation(order)
