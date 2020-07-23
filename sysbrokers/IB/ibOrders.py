

from copy import copy
from collections import  namedtuple
import datetime

from sysbrokers.IB.ibFuturesContracts import ibFuturesContractData
from syscore.objects import missing_order, failure, success, missing_data, arg_not_supplied
from sysdata.futures.contracts import futuresContract
from sysdata.fx.spotfx import currencyValue
from sysexecution.broker_orders import brokerOrderStackData, brokerOrder, orderWithControls
from sysexecution.base_orders import  no_order_id, tradeQuantity


from syslogdiag.log import logtoscreen


class ibOrderWithControls(orderWithControls):
    def __init__(self, broker_order, control_object):
        self._order = broker_order
        self._control_object = control_object

    def update_order(self):
        original_order = self.order
        extractable_trade_object = extractedTradeInfo(self.control_object)
        updated_broker_order = extractable_trade_object.\
            broker_order_from_fill_with_passed_instrument_code(original_order.instrument_code)

        self._order = updated_broker_order


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

    def get_list_of_broker_orders(self, account_id=arg_not_supplied):
        """
        Get list of broker orders from IB, and return as my broker_order objects

        :return: list of brokerOrder objects
        """

        list_of_raw_orders = self.ibconnection.broker_get_orders(account_id=account_id)
        order_list = [self.create_broker_order_object(broker_trade_object_results) for broker_trade_object_results
                      in list_of_raw_orders]
        order_list = [order for order in order_list if order is not missing_order]

        return order_list

    def get_list_of_broker_orders_using_external_tempid(self, account_id = arg_not_supplied):
        """
        We replace the field 'tempid' with a key which allows us to match more easily against external orders

        :return: list of BrokerOrder objects
        """

        order_list = self.get_list_of_broker_orders(account_id = account_id)
        for order in order_list:
            order._order_info['broker_tempid'] = create_tempid_from_broker_details(order)

        return order_list

    def get_dict_of_orders_from_storage(self):
        dict_of_raw_orders = self._traded_object_store
        order_dict = dict([(key, extractable_trade_object.broker_order_with_stored_instrument_code())
                           for key, extractable_trade_object in dict_of_raw_orders.items()])

        return order_dict


    def put_order_on_stack(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: ibOrderWithControls or missing_order
        """
        placed_broker_trade_object = self.send_broker_order_to_IB(broker_order)

        if placed_broker_trade_object is missing_order:
            return missing_order

        extractable_trade_object = extractedTradeInfo(placed_broker_trade_object,
                                                  instrument_code=broker_order.instrument_code)
        placed_broker_order = extractable_trade_object.broker_order_with_IB_trade_details(broker_order)
        placed_broker_order.submit_datetime = datetime.datetime.now()

        ## We do this so we can cancel stuff and get things back more easily
        storage_key = placed_broker_order.broker_tempid
        self.add_traded_object_to_store(storage_key, extractable_trade_object)

        order_with_controls = ibOrderWithControls(placed_broker_order, placed_broker_trade_object)

        return order_with_controls

    def send_broker_order_to_IB(self, broker_order):
        """

        :param broker_order: key properties are instrument_code, contract_id, quantity
        :return: int with order ID or missing_order

        """

        log = broker_order.log_with_attributes(self.log)
        log.msg("Going to submit order %s to IB" % str(broker_order))
        instrument_code = broker_order.instrument_code

        ## Next two are because we are a single leg order, but both are lists
        contract_id = broker_order.contract_id
        trade_list = broker_order.trade.qty

        order_type = broker_order.order_type
        limit_price = broker_order.limit_price
        account = broker_order.broker_account

        contract_object = futuresContract(instrument_code, contract_id)
        contract_object_with_ib_data = self.futures_contract_data.get_contract_object_with_IB_metadata(contract_object)

        placed_broker_trade_object = self.ibconnection.broker_submit_order(contract_object_with_ib_data, trade_list, account,
                                                  order_type = order_type,
                                                  limit_price = limit_price)
        if placed_broker_trade_object is missing_order:
            log.warn("Couldn't submit order")
            return missing_order

        log.msg("Order submitted to IB")

        return placed_broker_trade_object


    def create_broker_order_object(self, broker_trade_object_results):
        """
        Map from the data IB gives us to my broker order object

        :param broker_trade_object_results: tradeWithContract
        :return: brokerOrder
        """
        extractable_trade_object = extractedTradeInfo(broker_trade_object_results)
        instrument_code=self.futures_contract_data.\
            get_instrument_code_from_broker_code(extractable_trade_object.ib_instrument_code)

        broker_order = extractable_trade_object.broker_order_from_fill_with_passed_instrument_code(instrument_code)

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
        account_id = broker_order_to_match.broker_account
        list_of_broker_orders = self.get_list_of_broker_orders(account_id = account_id)
        matched_order = match_order_on_tempid(list_of_broker_orders,  broker_order_to_match)
        if matched_order is not missing_order:
            return matched_order

        ## Match on permid
        matched_order = match_order_on_permid(list_of_broker_orders, broker_order_to_match)

        return matched_order


    def cancel_order_on_stack(self, broker_order, account_id = arg_not_supplied):

        matched_order = self.match_db_broker_order_to_order_from_brokers(broker_order)
        if matched_order is missing_order:
            return failure

        original_order_object = matched_order.broker_objects['order']
        self.ibconnection.ib_cancel_order(original_order_object)

        return success

    def cancel_order_given_control_object(self, broker_orders_with_controls):
        original_order_object = broker_orders_with_controls.control_object.trade.order
        self.ibconnection.ib_cancel_order(original_order_object)

        return success

    def check_order_is_cancelled(self, broker_order):
        matched_order = self.match_db_broker_order_to_order_from_brokers(broker_order)
        if matched_order is missing_order:
            return failure
        original_order_object = matched_order.broker_objects['order']
        cancellation_status = self.ibconnection.ib_check_order_is_cancelled(original_order_object)

        return cancellation_status

    def check_order_is_cancelled_given_control_object(self, broker_order_with_controls):
        original_trade_object = broker_order_with_controls.control_object.trade
        cancellation_status = self.ibconnection.ib_check_order_is_cancelled(original_trade_object)

        return cancellation_status

    def modify_limit_price_given_control_object(self, broker_order_with_controls, new_limit_price):
        """
        NOTE this does not update the internal state of orders, which will retain the original order

        :param broker_orders_with_controls:
        :param new_limit_price:
        :return:
        """
        original_order_object = broker_order_with_controls.control_object.trade.order
        original_contract_object_with_legs = broker_order_with_controls.control_object.ibcontract_with_legs
        new_trade_object = self.ibconnection.modify_limit_price_given_original_objects(
                                                  original_order_object, original_contract_object_with_legs,
                                                  new_limit_price)

        original_placed_broker_order = broker_order_with_controls.order
        original_placed_broker_order.limit_price = new_limit_price

        extractable_trade_object = extractedTradeInfo(new_trade_object,
                                                  instrument_code=original_placed_broker_order.instrument_code)

        ## Update the object in the store
        storage_key = original_placed_broker_order.broker_tempid
        self.add_traded_object_to_store(storage_key, extractable_trade_object)

        new_order_with_controls = ibOrderWithControls(original_placed_broker_order, new_trade_object)

        return new_order_with_controls


class extractedTradeInfo(object):
    """
    Intermediate class that sucks all of the data out of the objects IB returns from eithier a trade done
      or orders requested, arranges it nicely.

      We then store this for future reference, plus it can very easily be turned into a broker order

    """

    def __init__(self, placed_broker_trade_object, instrument_code=None):
        """

        :param placed_broker_trade_object: tradeWithContract()
        """

        self._broker_trade_object = placed_broker_trade_object
        self.instrument_code = instrument_code

    def __repr__(self):
        return self._broker_trade_object.__repr__

    def extract_trade_info(self):
        return extract_trade_info(self._broker_trade_object)

    def broker_order_with_IB_trade_details(self, broker_order):
        ib_broker_order = self.broker_order_from_fill_with_passed_instrument_code(broker_order.instrument_code)
        placed_broker_order = add_trade_info_to_broker_order(broker_order, ib_broker_order)
        return placed_broker_order

    def broker_order_with_stored_instrument_code(self):
        if self.instrument_code is None:
            raise Exception("Instrument code needs storing through broker_order_with_IB_trade_details() call first")
        else:
            return self.broker_order_from_fill_with_passed_instrument_code(self.instrument_code)

    def broker_order_from_fill_with_passed_instrument_code(self, instrument_code):
        ib_broker_order = ibBrokerOrder.from_broker_trade_object(
                                                                 self.extract_trade_info(),
                                                                instrument_code = instrument_code)
        return ib_broker_order

    @property
    def ib_instrument_code(self):
        extracted = self.extract_trade_info()
        return extracted.contract.ib_instrument_code

    @property
    def instrument_code(self):
        return getattr(self, "_instrument_code", None)

    @instrument_code.setter
    def instrument_code(self, instrument_code):
        self._instrument_code = instrument_code

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
    def from_broker_trade_object(ibBrokerOrder,  extracted_trade_data, instrument_code=arg_not_supplied):
        sec_type = extracted_trade_data.contract.ib_sectype

        if sec_type not in ["FUT", "BAG"]:
            ## Doesn't handle non futures trades, just ignores them
            return missing_order

        strategy_name = ""
        if instrument_code is arg_not_supplied:
            instrument_code = extracted_trade_data.contract.ib_instrument_code
        contract_id_list = extracted_trade_data.contract.ib_contract_id

        algo_comment = extracted_trade_data.algo_msg
        order_type = extracted_trade_data.order.type
        limit_price = extracted_trade_data.order.limit_price
        broker_account = extracted_trade_data.order.account
        broker_permid = extracted_trade_data.order.perm_id

        broker_objects = dict(order=extracted_trade_data.order.order_object, trade=extracted_trade_data.trade_object,
                              contract=extracted_trade_data.contract.contract_object)

        leg_ratios = extracted_trade_data.contract.leg_ratios

        # sometimes this is negative
        unsigned_remain_qty_scalar = extracted_trade_data.order.remain_qty

        # when it's negative this is often zero
        unsigned_total_qty_scalar = extracted_trade_data.order.total_qty
        if unsigned_remain_qty_scalar<0:
            total_qty = None
        else:
            # remain is not used... but the option is here
            #remain_qty_scalar = unsigned_remain_qty_scalar * extracted_trade_data.order.order_sign
            #remain_qty_list = [int(remain_qty_scalar * ratio) for ratio in leg_ratios]
            #remain_qty = tradeQuantity(remain_qty_list)

            total_qty_scalar = unsigned_total_qty_scalar * extracted_trade_data.order.order_sign
            total_qty_list = [int(total_qty_scalar * ratio) for ratio in leg_ratios]

            total_qty = tradeQuantity(total_qty_list)

        fill_totals = extract_totals_from_fill_data(extracted_trade_data.fills)

        if fill_totals is missing_data:
            fill_datetime = None
            fill = total_qty.zero_version()
            filled_price_list = None
            commission = None
            broker_tempid = extracted_trade_data.order.order_id
            broker_clientid = extracted_trade_data.order.client_id
        else:
            broker_clientid, broker_tempid, filled_price_dict, fill_datetime, commission, signed_qty_dict = fill_totals

            filled_price_list = [filled_price_dict[contractid] for contractid in contract_id_list]
            fill_list = [int(signed_qty_dict[contractid]) for contractid in contract_id_list]
            fill = tradeQuantity(fill_list)

        if total_qty is None:
            total_qty = fill

        broker_order = ibBrokerOrder(strategy_name, instrument_code, contract_id_list, total_qty, fill=fill,
                                     order_type=order_type, limit_price=limit_price, filled_price=filled_price_list,
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


def extract_totals_from_fill_data(list_of_fills):
    """
    Sum up info over fills
    :return: average_filled_price, commission (as list of tuples), total quantity filled

    """
    contract_id_list = [fill.contract_id for fill in list_of_fills]
    unique_contract_id_list = list(set(contract_id_list))
    unique_contract_id_list.sort()

    if len(list_of_fills) == 0:
        # broker_clientid, broker_tempid, filled_price_dict, fill_datetime, commission_list, signed_qty_dict
        return missing_data

    fill_data_by_contract = {}
    for contractid in unique_contract_id_list:
        list_of_fills_for_contractid = [fill for fill in list_of_fills if fill.contract_id == contractid]
        extracted_totals = extract_totals_from_fill_data_for_contract_id(list_of_fills_for_contractid)
        fill_data_by_contract[contractid]= extracted_totals

    #  Returns tuple broker_clientid, broker_tempid, filled_price, fill_datetime, commission (as list of tuples), signed_qty
    first_contract = unique_contract_id_list[0]
    broker_clientid = fill_data_by_contract[first_contract][0]  # should all be the same
    broker_tempid = fill_data_by_contract[first_contract][1]  # should all be the same
    filled_price_dict = dict([(contractid, fill_data_for_contractid[2])
                              for contractid, fill_data_for_contractid
                              in fill_data_by_contract.items()])
    fill_datetime = fill_data_by_contract[first_contract][3]  # should all be the same
    commission_list_of_lists = [fill_data_for_contract[4] for fill_data_for_contract in fill_data_by_contract.values()]
    commission_list = sum(commission_list_of_lists, [])
    signed_qty_dict = dict([(contractid, fill_data_for_contractid[5])
                            for contractid, fill_data_for_contractid
                            in fill_data_by_contract.items()])

    return broker_clientid, broker_tempid, filled_price_dict, fill_datetime, commission_list, signed_qty_dict


def extract_totals_from_fill_data_for_contract_id(list_of_fills_for_contractid):
    """
    Sum up info over fills

    :param list_of_fills: list of named tuples
    :return: broker_clientid, broker_tempid, filled_price, fill_datetime, commission (as list of tuples)
    """
    qty_and_price_and_datetime_and_id = [(fill.cum_qty, fill.avg_price, fill.time,
                                          fill.temp_id, fill.client_id, fill.signed_qty) for fill in
                                         list_of_fills_for_contractid]

    ## sort by total quantity
    qty_and_price_and_datetime_and_id.sort(key=lambda x: x[0])

    final_fill = qty_and_price_and_datetime_and_id[-1]
    _, filled_price, fill_datetime, broker_tempid, broker_clientid, signed_qty = final_fill

    commission = [currencyValue(fill.commission_ccy, fill.commission) for fill in list_of_fills_for_contractid]

    return broker_clientid, broker_tempid, filled_price, fill_datetime, commission, signed_qty


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




def extract_trade_info(placed_broker_trade_object):
    trade_to_process = placed_broker_trade_object.trade
    legs = placed_broker_trade_object.ibcontract_with_legs.legs
    order_info = extract_order_info(trade_to_process)
    contract_info = extract_contract_info(trade_to_process, legs)
    fill_info = extract_fill_info(trade_to_process)

    algo_msg = " ".join([str(log_entry) for log_entry in trade_to_process.log])
    active = trade_to_process.isActive()

    tradeInfo = namedtuple("tradeInfo", ['order', 'contract', 'fills','algo_msg', 'active',
                                         'trade_object'])
    trade_info = tradeInfo(order_info, contract_info, fill_info, algo_msg, active, trade_to_process)

    return trade_info


def extract_order_info(trade_to_process):
    order = trade_to_process.order

    account = order.account
    perm_id = order.permId
    client_id = order.clientId
    limit_price = order.lmtPrice
    order_sign = sign_from_BS(order.action)
    order_type = resolve_order_type(order.orderType)
    order_id = order.orderId
    remain_qty = trade_to_process.remaining()
    total_qty = trade_to_process.order.totalQuantity

    orderInfo = namedtuple('orderInfo', ['account',  'perm_id', 'limit_price', 'order_sign', 'type',
                                         'remain_qty', 'order_object', 'client_id', 'order_id',
                                         'total_qty'])
    order_info = orderInfo(account=account, perm_id=perm_id, limit_price=limit_price,
                order_sign=order_sign, type = order_type, remain_qty=remain_qty, order_object = order,
                           client_id=client_id, order_id = order_id, total_qty = total_qty)

    return order_info

def extract_contract_info(trade_to_process, legs):
    contract = trade_to_process.contract
    ib_instrument_code = contract.symbol
    ib_sectype = contract.secType

    is_combo_legs = not legs==[]
    if is_combo_legs:
        ib_contract_id, leg_ratios = get_combo_info(contract, legs)
    else:
        ib_contract_id = [contract.lastTradeDateOrContractMonth]
        leg_ratios = [1]

    contractInfo = namedtuple("contractInfo", ['ib_instrument_code', 'ib_contract_id', 'ib_sectype', 'contract_object', 'legs', 'leg_ratios'])
    contract_info = contractInfo(ib_instrument_code=ib_instrument_code, ib_contract_id=ib_contract_id,
                                 ib_sectype=ib_sectype, contract_object=contract, legs=legs, leg_ratios = leg_ratios)

    return contract_info

def get_combo_info(contract, legs):
    ib_contract_id = [leg.lastTradeDateOrContractMonth for leg in legs]
    leg_ratios = [get_leg_ratio_for_leg(contract_id, contract, legs) for contract_id in ib_contract_id]

    return ib_contract_id, leg_ratios

def get_leg_ratio_for_leg(contract_id, contract, legs):
    ib_contract_id = [leg.lastTradeDateOrContractMonth for leg in legs]
    ib_conId =[leg.conId for leg in legs]
    idx = ib_contract_id.index(contract_id)
    conId = ib_conId[idx]

    contract_conId_list = [combo_leg.conId for combo_leg in contract.comboLegs]
    relevant_combo_leg_idx = contract_conId_list.index(conId)

    relevant_combo_leg = contract.comboLegs[relevant_combo_leg_idx]
    action = relevant_combo_leg.action
    ratio = relevant_combo_leg.ratio
    trade_sign = sign_from_BS(action)

    return trade_sign * ratio

def extract_contract_spread_info(trade_to_process):
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
    fill_info_without_bags = [single_fill for single_fill in fill_info if single_fill is not None]

    return fill_info_without_bags

def extract_single_fill(single_fill):
    is_bag_fill = single_fill.contract.secType == "BAG"
    if is_bag_fill:
        return None
    commission = single_fill.commissionReport.commission
    commission_ccy = single_fill.commissionReport.currency
    cum_qty = single_fill.execution.cumQty
    sign = sign_from_BOT_SEL(single_fill.execution.side)
    signed_qty = cum_qty * sign
    price = single_fill.execution.price
    avg_price = single_fill.execution.avgPrice
    time = single_fill.execution.time
    temp_id = single_fill.execution.orderId
    client_id = single_fill.execution.clientId
    contract_month = single_fill.contract.lastTradeDateOrContractMonth

    singleFill = namedtuple("singleFill", ['commission','commission_ccy', 'cum_qty', 'price', 'avg_price', 'time',
                                           'temp_id', 'client_id', 'signed_qty', 'contract_id'])

    single_fill = singleFill(commission, commission_ccy, cum_qty, price, avg_price, time, temp_id, client_id,
                             signed_qty, contract_month)

    return single_fill

def resolve_order_type(ib_order_type):
    lookup_dict = dict(MKT='market')
    my_order_type = lookup_dict.get(ib_order_type, "")

    return my_order_type


def sign_from_BS(action):
    if action=="SELL":
        return -1
    return 1

def sign_from_BOT_SEL(action):
    if action=="BOT":
        return 1
    return -1