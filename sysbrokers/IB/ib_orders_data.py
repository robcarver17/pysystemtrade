import datetime

from copy import copy

from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_translate_broker_order_objects import (
    create_broker_order_from_control_object,
)
from syscore.objects import missing_order, failure, success, arg_not_supplied
from sysobjects.contracts import futuresContract
from sysexecution.broker_orders import brokerOrderStackData, orderWithControls

from syslogdiag.log import logtoscreen


class ibOrderWithControls(orderWithControls):
    def __init__(
        self,
        control_object,
        ibconnection,
        broker_order=None,
        instrument_code=None,
        ticker_object=None,
        reference_of_controlling_algo=None,
    ):
        if broker_order is None:
            # This might happen if for example we are getting the orders from
            # IB
            self._order = create_broker_order_from_control_object(
                control_object, instrument_code
            )
        else:
            self._order = broker_order

        self._control_object = control_object
        self._ibconnection = ibconnection

        self._ticker = ticker_object
        self._reference_of_controlling_algo = reference_of_controlling_algo

        # this is different from the order submission date, that will be in IB timestamp land
        # this  is only used for local timing
        self._date_submitted = datetime.datetime.now()

    def write_placed_broker_trade_info_in_broker_order(self):
        ib_broker_order = create_broker_order_from_control_object(
            self.control_object, self.order.instrument_code
        )
        updated_broker_order = write_placed_broker_trade_info_in_broker_order(
            self.order, ib_broker_order
        )

        self._order = updated_broker_order

    def update_order(self):
        # Update the broker order using the control object
        # Can be used when first submitted, or when polling objects
        # Basically copies across the details from the control object that are
        # likely to be updated
        self._ibconnection.refresh()
        ib_broker_order = create_broker_order_from_control_object(
            self.control_object, self.order.instrument_code
        )
        updated_broker_order = add_trade_info_to_broker_order(
            self.order, ib_broker_order
        )

        self._order = updated_broker_order

    def broker_limit_price(self):
        self._ibconnection.refresh()
        ib_broker_order = create_broker_order_from_control_object(
            self.control_object, self.order.instrument_code
        )
        if ib_broker_order.limit_price == 0.0:
            broker_limit_price = None
        else:
            broker_limit_price = ib_broker_order.limit_price

        return broker_limit_price


class ibOrdersData(brokerOrderStackData):
    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        super().__init__(log=log)

        self._traded_object_store = dict()

    def add_order_with_controls_to_store(self, order_with_controls):
        storage_key = order_with_controls.order.broker_tempid
        self._traded_object_store[storage_key] = order_with_controls

    def __repr__(self):
        return "IB orders %s" % str(self.ibconnection)

    @property
    def futures_contract_data(self):
        return ibFuturesContractData(self.ibconnection)

    @property
    def futures_instrument_data(self):
        return ibFuturesInstrumentData(self.ibconnection)


    def get_list_of_broker_orders(self, account_id=arg_not_supplied):
        """
        Get list of broker orders from IB, and return as my broker_order objects

        :return: list of brokerOrder objects
        """
        list_of_control_objects = self.get_list_of_broker_control_orders(
            account_id=account_id
        )
        order_list = [
            order_with_control.order for order_with_control in list_of_control_objects]

        return order_list

    def get_dict_of_broker_control_orders(self, account_id=arg_not_supplied):
        control_order_list = self.get_list_of_broker_control_orders(
            account_id=account_id
        )
        dict_of_control_orders = dict(
            [
                (control_order.order.broker_tempid, control_order)
                for control_order in control_order_list
            ]
        )
        return dict_of_control_orders

    def get_list_of_broker_control_orders(self, account_id=arg_not_supplied):
        """
        Get list of broker orders from IB, and return as dict of control objects

        :return: list of brokerOrder objects
        """

        list_of_raw_orders_as_trade_objects = self.ibconnection.broker_get_orders(
            account_id=account_id)
        control_order_list = [
            self.create_broker_control_order_object(broker_trade_object_results)
            for broker_trade_object_results in list_of_raw_orders_as_trade_objects
        ]

        return control_order_list

    def create_broker_control_order_object(self, broker_trade_object_results):
        """
        Map from the data IB gives us to my broker order object, to order with controls

        :param broker_trade_object_results: tradeWithContract
        :return: brokerOrder
        """
        instrument_code = (
            self.futures_instrument_data.get_instrument_code_from_broker_code(
                broker_trade_object_results.ib_instrument_code
            )
        )
        broker_order_with_controls = ibOrderWithControls(
            broker_trade_object_results,
            self.ibconnection,
            instrument_code=instrument_code,
        )

        return broker_order_with_controls

    def get_list_of_orders_from_storage(self):
        dict_of_stored_orders = self.get_dict_of_orders_from_storage()

        return list(dict_of_stored_orders.values())

    def get_dict_of_orders_from_storage(self):
        # Get dict from storage, update, return just the orders
        dict_of_orders_with_control = self.get_dict_of_control_orders_from_storage()
        order_dict = dict(
            [
                (key, order_with_control.order)
                for key, order_with_control in dict_of_orders_with_control.items()
            ]
        )

        return order_dict

    def get_dict_of_control_orders_from_storage(self):
        dict_of_orders_with_control = self._traded_object_store
        __ = [
            order_with_control.update_order()
            for order_with_control in dict_of_orders_with_control.values()
        ]

        return dict_of_orders_with_control

    def put_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: ibOrderWithControls or missing_order
        """
        placed_broker_trade_object = self.send_broker_order_to_IB(broker_order)
        order_time = self.ibconnection.get_broker_time_local_tz()

        if placed_broker_trade_object is missing_order:
            return missing_order

        placed_broker_order_with_controls = ibOrderWithControls(
            placed_broker_trade_object,
            self.ibconnection,
            broker_order=broker_order)
        placed_broker_order_with_controls.order.submit_datetime = order_time

        # We do this so the tempid and commission are accurate
        placed_broker_order_with_controls.write_placed_broker_trade_info_in_broker_order()

        # We do this so we can cancel stuff and get things back more easily
        self.add_order_with_controls_to_store(placed_broker_order_with_controls)

        return placed_broker_order_with_controls

    def send_broker_order_to_IB(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: tradeWithContract object or missing_order

        """

        log = broker_order.log_with_attributes(self.log)
        log.msg("Going to submit order %s to IB" % str(broker_order))
        instrument_code = broker_order.instrument_code

        # Next two are because we are a single leg order, but both are lists
        contract_id = broker_order.contract_id
        trade_list = broker_order.trade.qty

        order_type = broker_order.order_type
        limit_price = broker_order.limit_price
        account = broker_order.broker_account

        contract_object = futuresContract(instrument_code, contract_id)
        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_metadata(
                contract_object
            )
        )

        placed_broker_trade_object = self.ibconnection.broker_submit_order(
            contract_object_with_ib_data,
            trade_list,
            account,
            order_type=order_type,
            limit_price=limit_price,
        )
        if placed_broker_trade_object is missing_order:
            log.warn("Couldn't submit order")
            return missing_order

        log.msg("Order submitted to IB")

        return placed_broker_trade_object

    def match_db_broker_order_to_order_from_brokers(
            self, broker_order_to_match):
        matched_control_order = (
            self.match_db_broker_order_to_control_order_from_brokers(
                broker_order_to_match
            )
        )
        if matched_control_order is missing_order:
            return missing_order

        broker_order = matched_control_order.order

        return broker_order

    def match_db_broker_order_to_control_order_from_brokers(
        self, broker_order_to_match
    ):
        """

        :return: brokerOrder coming from broker
        """

        # check stored orders
        dict_of_stored_control_orders = self.get_dict_of_control_orders_from_storage()
        matched_control_order = match_control_order_from_dict(
            dict_of_stored_control_orders, broker_order_to_match
        )
        if matched_control_order is not missing_order:
            return matched_control_order

        # try getting from broker
        # match on temp id and clientid
        account_id = broker_order_to_match.broker_account

        dict_of_broker_control_orders = self.get_dict_of_broker_control_orders(
            account_id=account_id
        )
        matched_control_order = match_control_order_from_dict(
            dict_of_broker_control_orders, broker_order_to_match
        )
        if matched_control_order is not missing_order:
            return matched_control_order

        # Match on permid
        matched_control_order = match_control_order_on_permid(
            dict_of_broker_control_orders, broker_order_to_match
        )

        return matched_control_order

    def cancel_order_on_stack(self, broker_order):

        matched_control_order = (
            self.match_db_broker_order_to_control_order_from_brokers(broker_order))
        if matched_control_order is missing_order:
            return failure
        self.cancel_order_given_control_object(matched_control_order)

        return success

    def cancel_order_given_control_object(self, broker_orders_with_controls):
        original_order_object = broker_orders_with_controls.control_object.trade.order
        self.ibconnection.ib_cancel_order(original_order_object)

        return success

    def check_order_is_cancelled(self, broker_order):
        matched_control_order = (
            self.match_db_broker_order_to_control_order_from_brokers(broker_order))
        if matched_control_order is missing_order:
            return failure
        cancellation_status = self.check_order_is_cancelled_given_control_object(
            matched_control_order)

        return cancellation_status

    def check_order_is_cancelled_given_control_object(
            self, broker_order_with_controls):
        status = self.get_status_for_control_object(broker_order_with_controls)
        cancellation_status = status == "Cancelled"

        return cancellation_status

    def check_order_can_be_modified_given_control_object(
        self, broker_order_with_controls
    ):
        status = self.get_status_for_control_object(broker_order_with_controls)
        modification_status = status in ["Submitted"]
        return modification_status

    def get_status_for_control_object(self, broker_order_with_controls):
        original_trade_object = broker_order_with_controls.control_object.trade
        status = self.get_status_for_trade_object(original_trade_object)

        return status

    def get_status_for_trade_object(self, original_trade_object):
        self.ibconnection.refresh()
        return original_trade_object.orderStatus.status

    def modify_limit_price_given_control_object(
        self, broker_order_with_controls, new_limit_price
    ):
        """
        NOTE this does not update the internal state of orders, which will retain the original order

        :param broker_orders_with_controls:
        :param new_limit_price:
        :return:
        """
        original_order_object = broker_order_with_controls.control_object.trade.order
        original_contract_object_with_legs = (
            broker_order_with_controls.control_object.ibcontract_with_legs
        )
        new_trade_object = self.ibconnection.modify_limit_price_given_original_objects(
            original_order_object, original_contract_object_with_legs, new_limit_price
        )

        # we don't actually replace the trade object
        # otherwise if the limit order isn't changed, it will think it has been
        broker_order_with_controls.order.limit_price = new_limit_price
        broker_order_with_controls.update_order()

        return broker_order_with_controls


def write_placed_broker_trade_info_in_broker_order(
    broker_order, broker_order_from_trade_object
):
    new_broker_order = copy(broker_order)
    keys_to_replace = [
        "broker_permid",
        "broker_account",
        "broker_clientid",
        "commission",
        "broker_permid",
        "broker_tempid",
    ]

    for key in keys_to_replace:
        new_broker_order._order_info[key] = broker_order_from_trade_object._order_info[
            key
        ]

    return new_broker_order


def add_trade_info_to_broker_order(
        broker_order,
        broker_order_from_trade_object):
    new_broker_order = copy(broker_order)
    keys_to_replace = ["broker_permid", "commission", "algo_comment"]

    for key in keys_to_replace:
        new_broker_order._order_info[key] = broker_order_from_trade_object._order_info[
            key
        ]

    broker_order_is_filled = not broker_order_from_trade_object.fill.equals_zero()
    if broker_order_is_filled:
        new_broker_order.fill_order(
            broker_order_from_trade_object.fill,
            broker_order_from_trade_object.filled_price,
            broker_order_from_trade_object.fill_datetime,
        )

    return new_broker_order


def match_control_order_on_permid(
        dict_of_broker_control_orders,
        broker_order_to_match):
    list_of_broker_control_orders = dict_of_broker_control_orders.values()
    list_of_broker_orders = [
        control_order.order for control_order in list_of_broker_control_orders
    ]

    permid_to_match = broker_order_to_match.broker_permid
    if permid_to_match == "" or permid_to_match == 0:
        return missing_order

    permid_list = [order.broker_permid for order in list_of_broker_orders]
    try:
        permid_idx = permid_list.index(permid_to_match)
    except ValueError:
        return missing_order

    matched_control_order = list_of_broker_control_orders[permid_idx]

    return matched_control_order


def match_control_order_from_dict(
        dict_of_broker_control_orders,
        broker_order_to_match):

    matched_control_order_from_dict = dict_of_broker_control_orders.get(
        broker_order_to_match.broker_tempid, missing_order
    )

    return matched_control_order_from_dict
