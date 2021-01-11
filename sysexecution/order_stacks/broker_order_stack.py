import datetime

from syscore.objects import failure, missing_order
from sysexecution.order_stacks.order_stack import orderStackData


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