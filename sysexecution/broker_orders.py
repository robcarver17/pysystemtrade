from copy import copy
import datetime
from sysexecution.order_stack import orderStackData
from sysexecution.base_orders import (
    no_order_id,
    no_children,
    no_parent,
    resolve_trade_fill_fillprice,
)
from sysexecution.contract_orders import contractOrder, contractTradeableObject

from syscore.genutils import none_to_object, object_to_none
from syscore.objects import failure, missing_order, fill_exceeds_trade, success


class brokerOrder(contractOrder):
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
        algo_used="",
        order_type="market",
        limit_price=None,
        filled_price=None,
        submit_datetime=None,
        fill_datetime=None,
        side_price=None,
        mid_price=None,
        algo_comment="",
        broker="",
        broker_account="",
        broker_clientid="",
        commission=0.0,
        broker_permid="",
        broker_tempid="",
        manual_fill=False,
        calendar_spread_order=None,
        split_order=False,
        sibling_id_for_split_order=None,
        roll_order=False,
        broker_objects=dict()
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

        tradeable_object, trade = super()._resolve_args(args)
        self._tradeable_object = tradeable_object

        (
            resolved_trade,
            resolved_fill,
            resolved_filled_price,
        ) = resolve_trade_fill_fillprice(trade, fill, filled_price)

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
            algo_used=algo_used,
            order_type=order_type,
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
            roll_order=roll_order,
        )

        # NOTE: we do not include these in the normal order info dict
        # This means they will NOT be saved when we do .as_dict(), i.e. they won't be saved in the mongo record
        # This is deliberate since these objects can't be saved accordingly
        # Instead we store them only in a single session to make it easier to
        # match and modify orders

        self._broker_objects = broker_objects


    @property
    def algo_used(self):
        return self._order_info["algo_used"]

    @property
    def broker_objects(self):
        return self._broker_objects

    @property
    def order_type(self):
        return self._order_info["order_type"]

    @property
    def submit_datetime(self):
        return self._order_info["submit_datetime"]

    @submit_datetime.setter
    def submit_datetime(self, submit_datetime):
        self._order_info["submit_datetime"] = submit_datetime

    @property
    def manual_fill(self):
        return self._order_info["manual_fill"]

    @manual_fill.setter
    def manual_fill(self, manual_fill):
        self._order_info["manual_fill"] = manual_fill

    @property
    def calendar_spread_order(self):
        return self._order_info["calendar_spread_order"]

    @property
    def side_price(self):
        return self._order_info["side_price"]

    @property
    def mid_price(self):
        return self._order_info["mid_price"]

    @property
    def algo_comment(self):
        return self._order_info["algo_comment"]

    @algo_comment.setter
    def algo_comment(self, comment):
        self._order_info["algo_comment"] = comment

    @property
    def broker(self):
        return self._order_info["broker"]

    @property
    def broker_account(self):
        return self._order_info["broker_account"]

    @property
    def broker_permid(self):
        return self._order_info["broker_permid"]

    @broker_permid.setter
    def broker_permid(self, permid):
        self._order_info["broker_permid"] = permid

    @property
    def broker_clientid(self):
        return self._order_info["broker_clientid"]

    @broker_clientid.setter
    def broker_clientid(self, broker_clientid):
        self._order_info["broker_clientid"] = broker_clientid

    @property
    def broker_tempid(self):
        return self._order_info["broker_tempid"]

    @broker_tempid.setter
    def broker_tempid(self, broker_tempid):
        self._order_info["broker_tempid"] = broker_tempid

    @property
    def commission(self):
        return self._order_info["commission"]

    @commission.setter
    def commission(self, comm):
        self._order_info["commission"] = comm

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

        order = brokerOrder(
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
            filled_price=filled_price,
            fill_datetime=fill_datetime,
            **order_info
        )

        return order

    # Following methods for compatibility with parent class

    @property
    def roll_order(self):
        return False

    @property
    def inter_spread_order(self):
        return False

    @property
    def reference_price(self):
        return None

    @property
    def algo_to_use(self):
        return self.algo_used()

    @property
    def manual_trade(self):
        return False

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

    def split_spread_order(self):
        """

        :param self:
        :return: list of contract orders, will be original order if not a spread order
        """
        if len(self.contract_id) == 1:
            # not a spread trade
            return [self]

        list_of_derived_broker_orders = []
        original_as_dict = self.as_dict()
        for contractid, trade_qty, fill, fill_price, mid_price, side_price in zip(
            self.contract_id,
            self.trade,
            self.fill,
            self.filled_price,
            self.mid_price,
            self.side_price,
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
            new_order_as_dict["mid_price"] = mid_price
            new_order_as_dict["side_price"] = side_price

            new_order = brokerOrder.from_dict(new_order_as_dict)
            new_order.split_order(self.order_id)

            list_of_derived_broker_orders.append(new_order)

        return list_of_derived_broker_orders


def create_new_broker_order_from_contract_order(
    contract_order,
    order_type="market",
    limit_price=None,
    submit_datetime=None,
    side_price=None,
    mid_price=None,
    algo_comment="",
    broker="",
    broker_account="",
    broker_clientid="",
    broker_permid="",
    broker_tempid="",
):

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
    )

    return broker_order


class brokerOrderStackData(orderStackData):
    def __repr__(self):
        return "Broker order stack: %s" % str(self._stack)

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

    def add_execution_details_from_matched_broker_order(
        self, broker_order_id, matched_broker_order
    ):
        db_broker_order = self.get_order_with_id_from_stack(broker_order_id)
        db_broker_order.add_execution_details_from_matched_broker_order(
            matched_broker_order
        )
        self._change_order_on_stack(broker_order_id, db_broker_order)

    def find_order_with_broker_tempid(self, broker_tempid):
        list_of_order_ids = self.get_list_of_order_ids(
            exclude_inactive_orders=False)
        for order_id in list_of_order_ids:
            order = self.get_order_with_id_from_stack(order_id)
            if order.broker_tempid == broker_tempid:
                return order

        return missing_order


class orderWithControls(object):
    """
    An encapsulation of a submitted broker order which includes additional methods for monitoring and controlling the orders progress
    The control object is a pointer to object(s) that allow us to do various things with the order at the broker end

    Control objects are broker specific, and some methods need to be implemented by the broker inherited method
    """

    def __init__(self, broker_order, control_object, ticker_object=None):
        self._order = broker_order
        self._control_object = control_object
        self._ticker = ticker_object

        # we don't use the broker order time, as it may not be in local TZ
        self._date_submitted = datetime.datetime.now()

    @property
    def ticker(self):
        return self._ticker

    def add_or_replace_ticker(self, new_ticker):
        self._ticker = new_ticker

    def set_submit_datetime(self, new_submit_datetime):
        self._order.submit_datetime = new_submit_datetime

    @property
    def control_object(self):
        return self._control_object

    def replace_control_object(self, new_control_object):
        self._control_object = new_control_object

    @property
    def order(self):
        return self._order

    @property
    def datetime_order_submitted(self):
        return self._date_submitted

    def message_required(self, messaging_frequency=30):
        time_elapsed = self.seconds_since_last_message()
        if time_elapsed > messaging_frequency:
            self.reset_last_message_time()
            return True

        return False

    def seconds_since_last_message(self):
        time_now = datetime.datetime.now()
        time_elapsed = time_now - self.last_message_time
        return time_elapsed.total_seconds()

    @property
    def last_message_time(self):
        last_time = getattr(self, "_last_message_time", None)
        if last_time is None:
            last_time = self.datetime_order_submitted

        return last_time

    def reset_last_message_time(self):
        self._last_message_time = datetime.datetime.now()

    def seconds_since_submission(self):
        time_now = datetime.datetime.now()
        time_elapsed = time_now - self.datetime_order_submitted
        return time_elapsed.total_seconds()

    def update_order(self):
        # Update the representation of the order based on the control object
        raise NotImplementedError

    @property
    def current_limit_price(self):
        current_limit_price = self.order.limit_price

        return current_limit_price

    def completed(self):
        self.update_order()
        return self.order.fill_equals_desired_trade()

    def check_limit_price_consistent(self):
        broker_limit_price = self.broker_limit_price()
        if broker_limit_price == self.order.limit_price:
            return True
        else:
            return False

    def broker_limit_price(self):
        raise NotImplementedError
