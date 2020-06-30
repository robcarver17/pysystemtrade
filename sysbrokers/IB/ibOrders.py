

from copy import copy
from collections import  namedtuple
import datetime

from sysbrokers.IB.ibFuturesContracts import ibFuturesContractData
from syscore.objects import missing_order, failure, success
from sysdata.futures.contracts import futuresContract
from sysdata.fx.spotfx import currencyValue
from sysexecution.broker_orders import brokerOrderStackData, brokerOrder
from sysexecution.base_orders import  no_order_id


from syslogdiag.log import logtoscreen

def add_trade_info_to_broker_order(broker_order, broker_order_from_trade_object):
    new_broker_order = copy(broker_order)
    keys_to_replace = ['submit_datetime', 'broker_permid', 'broker_account', 'broker_clientid',
                       'commission', 'broker_permid']

    for key in keys_to_replace:
        new_broker_order._order_info[key] = broker_order_from_trade_object._order_info[key]

    new_broker_order._order_info['broker_tempid'] = create_tempid_from_broker_details(broker_order_from_trade_object)

    return new_broker_order

def create_tempid_from_broker_details(broker_order_from_trade_object):
    tempid = "%s/%s/%s" % (broker_order_from_trade_object.broker_account,
                           broker_order_from_trade_object.broker_clientid,
                           broker_order_from_trade_object.broker_tempid)
    return tempid

def get_order_identification_from_tempid(broker_order):
    broker_account, broker_clientid, broker_tempid = broker_order.broker_tempid.split("/")
    broker_clientid = int(broker_clientid)
    broker_tempid = int(broker_tempid)

    return broker_account, broker_clientid, broker_tempid

class ibBrokerOrder(brokerOrder):

    @classmethod
    def from_broker_trade_object(ibBrokerOrder, instrument_code, broker_trade_object):
        sec_type = broker_trade_object.contract.ib_sectype
        if sec_type != "FUT":
            ## Doesn't handle non futures trades, just ignores them
            return missing_order

        strategy_name = ""

        contract_id = broker_trade_object.contract.ib_contract_id

        # NOT A SPREAD ORDER

        order_sign = broker_trade_object.order.order_sign
        remain_qty = broker_trade_object.order.remain_qty * order_sign
        fill = broker_trade_object.total_filled * order_sign
        trade_size = fill + remain_qty

        algo_comment = broker_trade_object.algo_msg
        order_type = broker_trade_object.order.type
        limit_price = broker_trade_object.order.limit_price
        broker_account = broker_trade_object.order.account
        broker_permid = broker_trade_object.order.order_object.permId
        broker_tempid = broker_trade_object.order.order_object.orderId
        broker_clientid = broker_trade_object.order.order_object.clientId

        broker_objects = dict(order=broker_trade_object.order.order_object, trade=broker_trade_object.trade_object,
                              contract=broker_trade_object.contract.contract_object)

        broker_order = ibBrokerOrder(strategy_name, instrument_code, [contract_id], [trade_size], fill=[fill],
                                   order_type=order_type, limit_price=limit_price,
                                   algo_comment=algo_comment,

                                   broker_account=broker_account,

                                   broker_permid=broker_permid, broker_tempid=broker_tempid,
                                   broker_clientid=broker_clientid,
                                     submit_datetime=datetime.datetime.now())

        broker_order.broker_objects = broker_objects

        return broker_order

    @classmethod
    def from_broker_fills_object(ibBrokerOrder, instrument_code, broker_trade_object):
        sec_type = broker_trade_object.contract.ib_sectype
        if sec_type != "FUT":
            ## Doesn't handle non futures trades, just ignores them
            return missing_order

        strategy_name = ""

        contract_id = broker_trade_object.contract.ib_contract_id

        # NOT A SPREAD ORDER

        order_sign = broker_trade_object.order.order_sign
        remain_qty = broker_trade_object.order.remain_qty * order_sign
        fill = broker_trade_object.total_filled * order_sign
        trade_size = fill + remain_qty

        algo_comment = broker_trade_object.algo_msg
        order_type = broker_trade_object.order.type
        limit_price = broker_trade_object.order.limit_price
        broker_account = broker_trade_object.order.account
        broker_permid = broker_trade_object.order.perm_id

        broker_objects = dict(order=broker_trade_object.order.order_object, trade=broker_trade_object.trade_object,
                              contract=broker_trade_object.contract.contract_object)

        broker_clientid, broker_tempid, filled_price, fill_datetime, commission = extract_totals_from_fill_data(
            broker_trade_object.fills)

        broker_order = ibBrokerOrder(strategy_name, instrument_code, [contract_id], [trade_size], fill=[fill],
                                   order_type=order_type, limit_price=limit_price, filled_price=filled_price,
                                   algo_comment=algo_comment,
                                   fill_datetime=fill_datetime,
                                   broker_account=broker_account,
                                   commission=commission,
                                   broker_permid=broker_permid, broker_tempid=broker_tempid,
                                   broker_clientid=broker_clientid)

        broker_order.broker_objects = broker_objects

        return broker_order

    @property
    def broker_objects(self):
        return getattr(self, "_broker_objects", None)

    @broker_objects.setter
    def broker_objects(self, broker_objects):
        self._broker_objects = broker_objects



def extract_totals_from_fill_data( list_of_fills):
    """
    Sum up info over fills

    :param list_of_fills: list of named tuples
    :return: average_filled_price, commission (as list of tuples), total quantity filled
    """
    if len(list_of_fills)==0:
        return no_order_id, no_order_id, None, None, 0.0

    qty_and_price_and_datetime_and_id = [(fill.cum_qty, fill.avg_price, fill.time,
                                          fill.temp_id, fill.client_id) for fill in list_of_fills]

    ## sort by total quantity
    qty_and_price_and_datetime_and_id.sort(key = lambda x:x[0])

    final_fill = qty_and_price_and_datetime_and_id[-1]
    _, filled_price, fill_datetime, broker_tempid, broker_clientid = final_fill

    commission = [currencyValue(fill.commission_ccy, fill.commission) for fill in list_of_fills]

    return broker_clientid, broker_tempid, filled_price, fill_datetime, commission


class ibOrdersData(brokerOrderStackData):
    def __init__(self, ibconnection, log=logtoscreen("ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

        self._traded_object_store = dict()

    def add_traded_object_to_store(self, key, traded_object):
        self._traded_object_store[key] = traded_object

    def __repr__(self):
        return "IB orders %s" % str(self.ibconnection)


    @property
    def futures_contract_data(self):
        return  ibFuturesContractData(self.ibconnection)

    def get_list_of_broker_orders(self):
        """
        Get list of broker orders from IB, and return as my broker_order objects

        :return: list of brokerOrder objects
        """

        list_of_raw_orders = self.ibconnection.broker_get_orders()
        order_list = [self.create_broker_order_object(raw_order) for raw_order in list_of_raw_orders]
        order_list = [order for order in order_list if order is not missing_order]

        return order_list

    def get_list_of_broker_orders_using_external_tempid(self):
        """
        We replace the field 'tempid' with a key which allows us to match more easily against external orders

        :return: list of BrokerOrder objects
        """

        order_list = self.get_list_of_broker_orders()
        for order in order_list:
            order._order_info['broker_tempid'] = create_tempid_from_broker_details(order)

        return order_list

    def get_dict_of_orders_from_storage(self):
        dict_of_raw_orders = self._traded_object_store
        order_dict = dict([(key, self.create_broker_order_object(raw_order))
                           for key, raw_order in dict_of_raw_orders.items()])

        return order_dict


    def put_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: placed_broker_order or missing_order
        """
        if len(broker_order.trade)>1:
            # only single legs!
            return missing_order

        placed_broker_trade_object = self.put_single_leg_order_on_stack(broker_order)

        if placed_broker_trade_object is missing_order:
            return missing_order

        extracted_trade_data = extract_trade_info(placed_broker_trade_object)
        broker_order_from_trade_object = ibBrokerOrder.from_broker_trade_object(broker_order.instrument_code,
                                                                     extracted_trade_data)

        placed_broker_order = add_trade_info_to_broker_order(broker_order, broker_order_from_trade_object)

        ## We do this so we can cancel stuff and get things back more easily
        storage_key = placed_broker_order.broker_tempid
        self.add_traded_object_to_store(storage_key, placed_broker_trade_object)

        return placed_broker_order

    def put_single_leg_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: int with order ID or missing_order

        """

        log = broker_order.log_with_attributes(self.log)
        log.msg("Going to submit order %s to IB" % str(broker_order))
        instrument_code = broker_order.instrument_code

        ## Next two are because we are a single leg order, but both are lists
        contract_id = broker_order.contract_id[0]
        trade = broker_order.trade[0]

        order_type = broker_order.order_type
        limit_price = broker_order.limit_price
        account = broker_order.broker_account

        contract_object = futuresContract(instrument_code, contract_id)
        contract_object_with_ib_data = self.futures_contract_data.get_contract_object_with_IB_metadata(contract_object)

        placed_broker_trade_object = self.ibconnection.broker_submit_single_leg_order(contract_object_with_ib_data, trade, account,
                                                  order_type = order_type,
                                                  limit_price = limit_price)
        if placed_broker_trade_object is missing_order:
            log.warn("Couldn't submit order")
            return missing_order

        log.msg("Order submitted to IB")

        return placed_broker_trade_object

    def create_broker_order_object(self, broker_trade_object_after_submission):
        """
        Map from the data IB gives us to my broker order object

        :param broker_trade_object_after_submission: named tuple with fields defined in ibClient
        :return: brokerOrder
        """
        trade_info = extract_trade_info(broker_trade_object_after_submission)
        instrument_code=self.futures_contract_data.\
            get_instrument_code_from_broker_code(trade_info.contract.ib_instrument_code)

        broker_order = ibBrokerOrder.from_broker_fills_object(instrument_code, trade_info)

        return broker_order


    def match_db_broker_order_to_order_from_brokers(self, broker_order_to_match):
        """

        :return: brokerOrder coming from broker
        """
        dict_of_broker_orders = self.get_dict_of_orders_from_storage()
        matched_order = match_order_from_dict(dict_of_broker_orders, broker_order_to_match)
        if matched_order is not missing_order:
            return matched_order

        ## match on temp id and clientid
        list_of_broker_orders = self.get_list_of_broker_orders()
        matched_order = match_order_on_tempid(list_of_broker_orders,  broker_order_to_match)
        if matched_order is not missing_order:
            return matched_order

        ## Match on permid
        matched_order = match_order_on_permid(list_of_broker_orders, broker_order_to_match)

        return matched_order


    def cancel_order_on_stack(self, broker_order):

        matched_order = self.match_db_broker_order_to_order_from_brokers(broker_order)
        if matched_order is missing_order:
            return failure

        original_order_object = matched_order.broker_objects['order']
        self.ibconnection.ib_cancel_order(original_order_object)

        return success

    def check_order_is_cancelled(self, broker_order):
        matched_order = self.match_db_broker_order_to_order_from_brokers(broker_order)
        if matched_order is missing_order:
            return failure
        original_order_object = matched_order.broker_objects['order']
        cancellation_status = self.ibconnection.ib_check_order_is_cancelled(original_order_object)

        return cancellation_status

    """
    The original modification code has been abandoned

    However at some point execution algos will need to modify orders: change limit price and cancel

    This code is left here since some of it will be reused

    def modify_limit_order_on_stack(self, broker_order, new_limit):

        matched_order = self.match_db_broker_order_to_order_from_brokers(broker_order)
        if matched_order is missing_order:
            return failure

        storage_key = broker_order.broker_tempid
        original_order_object = matched_order.broker_objects['order']
        original_contract_object = matched_order.broker_objects['contract']

        original_order_object.limitPrice = new_limit

            placed_broker_trade_object = self.ibconnection.\
                ib_modify_existing_order(original_order_object, original_contract_object)

        ## We do this so we can cancel stuff and get things back more easily
        self.add_traded_object_to_store(storage_key, placed_broker_trade_object)

        return success

    def cancel_order(self,  broker_order, original_order_object):
        placed_broker_trade_object = self.ibconnection.ib_cancel_order(original_order_object)

        return placed_broker_trade_object


    def check_to_see_if_broker_order_is_modified(self, broker_order):

        #psuedo code is get matched broker order and check traded object limit price
        # possibly also status messages

        return result


    def check_cancelled_order(self, matched_order):
    # possibly also check status messages if failed
        traded_object = matched_order.broker_objects['trade_object']
        if traded_object.orderStatus.status=='Cancelled':
            return True
        else:
            return None
    """


def match_order_on_permid(list_of_broker_orders, broker_order_to_match):
    permid_to_match = broker_order_to_match.broker_permid
    if permid_to_match == '' or permid_to_match == 0:
        return missing_order

    permid_list = [order.broker_permid for order in list_of_broker_orders]
    try:
        permid_idx = permid_list.index(permid_to_match)
    except  ValueError:
        return missing_order

    matched_order = list_of_broker_orders[permid_idx]

    return matched_order


def match_order_from_dict( dict_of_broker_orders,  broker_order_to_match):

    matched_order_from_dict = dict_of_broker_orders.get(broker_order_to_match.broker_tempid, missing_order)

    return matched_order_from_dict

def match_order_on_tempid(list_of_broker_orders, broker_order_to_match):

    broker_account, broker_clientid, broker_tempid = get_order_identification_from_tempid(broker_order_to_match)

    matched_order_list = [order for order in list_of_broker_orders
                          if order.broker_tempid == broker_tempid
                          and order.broker_clientid == broker_clientid
                          and order.broker_account == broker_account]
    if len(matched_order_list)>1:
        return missing_order
    if len(matched_order_list)==0:
        return missing_order

    matched_order = matched_order_list[0]

    return matched_order




def extract_trade_info(trade_to_process):
    order_info = extract_order_info(trade_to_process)
    contract_info = extract_contract_info(trade_to_process)
    fill_info = extract_fill_info(trade_to_process)

    algo_msg = " ".join([str(log_entry) for log_entry in trade_to_process.log])
    total_filled = trade_to_process.filled()
    active = trade_to_process.isActive()

    tradeInfo = namedtuple("tradeInfo", ['order', 'contract', 'fills','algo_msg', 'total_filled', 'active',
                                         'trade_object'])
    trade_info = tradeInfo(order_info, contract_info, fill_info, algo_msg, total_filled, active, trade_to_process)

    return trade_info

def extract_order_info(trade_to_process):
    order = trade_to_process.order

    account = order.account
    perm_id = order.permId
    limit_price = order.lmtPrice
    order_sign = sign_from_BS(order.action)
    order_type = resolve_order_type(order.orderType)
    remain_qty = trade_to_process.remaining()

    orderInfo = namedtuple('orderInfo', ['account',  'perm_id', 'limit_price', 'order_sign', 'type',
                                         'remain_qty', 'order_object'])
    order_info = orderInfo(account=account, perm_id=perm_id, limit_price=limit_price,
                order_sign=order_sign, type = order_type, remain_qty=remain_qty, order_object = order)

    return order_info

def extract_contract_info(trade_to_process):
    contract = trade_to_process.contract
    ib_instrument_code = contract.symbol
    ib_contract_id = contract.lastTradeDateOrContractMonth
    ib_sectype = contract.secType

    contractInfo = namedtuple("contractInfo", ['ib_instrument_code', 'ib_contract_id', 'ib_sectype', 'contract_object'])
    contract_info = contractInfo(ib_instrument_code=ib_instrument_code, ib_contract_id=ib_contract_id,
                                 ib_sectype=ib_sectype, contract_object=contract)

    return contract_info

def extract_fill_info(trade_to_process):
    all_fills = trade_to_process.fills
    fill_info = [extract_single_fill(single_fill) for single_fill in all_fills]

    return fill_info

def extract_single_fill(single_fill):
    commission = single_fill.commissionReport.commission
    commission_ccy = single_fill.commissionReport.currency
    cum_qty = single_fill.execution.cumQty
    price = single_fill.execution.price
    avg_price = single_fill.execution.avgPrice
    time = single_fill.execution.time
    temp_id = single_fill.execution.orderId
    client_id = single_fill.execution.clientId

    singleFill = namedtuple("singleFill", ['commission','commission_ccy', 'cum_qty', 'price', 'avg_price', 'time',
                                           'temp_id', 'client_id'])

    single_fill = singleFill(commission, commission_ccy, cum_qty, price, avg_price, time, temp_id, client_id)

    return single_fill

def resolve_order_type(ib_order_type):
    lookup_dict = dict(MKT='market')
    my_order_type = lookup_dict.get(ib_order_type, "")

    return my_order_type


def sign_from_BS(action):
    if action=="SELL":
        return -1
    return 1
