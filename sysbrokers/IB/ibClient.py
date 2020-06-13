import datetime
import pandas as pd
import re

from collections import namedtuple

from ib_insync import Forex, Future, util
from ib_insync.order import MarketOrder

from sysdata.fx.spotfx import currencyValue
from sysbrokers.baseClient import brokerClient
from syscore.genutils import NOT_REQUIRED
from syscore.objects import missing_contract, arg_not_supplied, missing_order
from syscore.dateutils import adjust_timestamp
from syslogdiag.log import logtoscreen


_PACING_PERIOD_SECONDS = 10*60
_PACING_PERIOD_LIMIT = 60
PACING_INTERVAL_SECONDS = 1+(_PACING_PERIOD_SECONDS  / _PACING_PERIOD_LIMIT)

STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY = 600

class ibClient(brokerClient):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, log=logtoscreen("ibClient")):

        self.log = log
        ## means our first call won't be throttled for pacing
        self.last_historic_price_calltime = datetime.datetime.now()-  datetime.timedelta(seconds=_PACING_PERIOD_SECONDS)


    def broker_get_orders(self):
        """
        Get all trades, orders and return them with the information needed

        :return: list
        """
        trades_in_broker_format = self.ib.trades()
        order_list = [extract_trade_info(trade_to_process) for trade_to_process in trades_in_broker_format]

        return order_list

    # Methods in parent class overriden here
    # These methods should abstract the broker completely
    def broker_submit_single_leg_order(self, contract_object_with_ib_data, trade, account,
                                                  order_type = "market",
                                                  limit_price = None):
        """

        :param ibcontract: contract_object_with_ib_broker_config: contract where instrument has ib metadata
        :param trade: int
        :param account: str
        :param order_type: str, market or limit
        :param limit_price: None or float

        :return: brokers trade object

        """

        if order_type=="market":
            trade_object = self.ib_submit_single_leg_market_order(contract_object_with_ib_data, trade, account)
        else:
            self.log.critical("Order type %s is not supported for order on %s" % (order_type, str(contract_object_with_ib_data)))
            return missing_order

        return trade_object

    def broker_get_positions(self):
        ## Get all the positions
        ## We return these as a dict of pd DataFrame
        ## dict entries are asset classes, columns are IB symbol, contract ID, contract expiry

        raw_positions = self.ib.positions()
        dict_of_positions = from_ib_positions_to_dict(raw_positions)

        return dict_of_positions

    def broker_get_futures_contract_list(self, instrument_object_with_ib_config):

        specific_log = self.log.setup(instrument_code = instrument_object_with_ib_config.instrument_code)

        ibcontract_pattern = ib_futures_instrument(instrument_object_with_ib_config)
        contract_list = self.ib_get_contract_chain(ibcontract_pattern, log=specific_log)
        # if no contracts found will be empty

        # Extract expiry date strings from these
        contract_dates = [ibcontract.lastTradeDateOrContractMonth for ibcontract in contract_list]

        return contract_dates



    def broker_get_daily_fx_data(self, ccy1, ccy2="USD", bar_freq="D"):
        """
        Get some spot fx data

        :param ccy1: first currency in pair
        :param ccy2: second currency in pair
        :return: pd.Series
        """

        ccy_code = ccy1 + ccy2
        specific_log = self.log.setup(currency_code = ccy_code)

        ibcontract = self.ib_spotfx_contract(ccy1, ccy2=ccy2, log=specific_log)
        # Register the contract to make logging and error handling cleaner
        # Two different ways of labelling
        self.add_contract_to_register(ibcontract,
                                      log_tags = dict(currency_code = ccy_code))

        if ibcontract is missing_contract:
            specific_log.warn("Can't find IB contract for %s%s" % (ccy1, ccy2))

        fx_data = self._get_generic_data_for_contract(ibcontract, log=specific_log, bar_freq=bar_freq,
                                                      whatToShow='MIDPOINT')

        return fx_data

    def broker_get_historical_futures_data_for_contract(self, contract_object_with_ib_broker_config, bar_freq="D"):
        """
        Get historical daily data

        :param contract_object_with_ib_broker_config: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """

        specific_log = self.log.setup(instrument_code = contract_object_with_ib_broker_config.instrument_code,
                                      contract_date = contract_object_with_ib_broker_config.date)

        ibcontract = self.ib_futures_contract(contract_object_with_ib_broker_config)
        if ibcontract is missing_contract:
            specific_log.warn("Can't resolve IB contract %s" % str(contract_object_with_ib_broker_config))

        price_data = self._get_generic_data_for_contract(ibcontract, log=specific_log, bar_freq=bar_freq,
                                                         whatToShow='TRADES')

        return price_data


    def broker_get_account_value_across_currency_across_accounts(self, account_id=arg_not_supplied):
        list_of_currencies = self.get_list_of_currencies_for_liquidation_values()
        list_of_values_per_currency = list([
            currencyValue(currency, self.get_liquidation_value_for_currency_across_accounts(currency))
            for currency in list_of_currencies])

        return list_of_values_per_currency


    def get_liquidation_value_for_currency_across_accounts(self, currency):
        liquidiation_values_across_accounts_dict = self.get_net_liquidation_value_across_accounts()
        list_of_account_ids = liquidiation_values_across_accounts_dict.keys()
        values_for_currency = [liquidiation_values_across_accounts_dict[account_id].get(currency, 0.0)
                                for account_id in list_of_account_ids]

        return sum(values_for_currency)

    def get_list_of_currencies_for_liquidation_values(self):
        liquidiation_values_across_accounts_dict = self.get_net_liquidation_value_across_accounts()
        currencies = [list(account_dict.keys()) for account_dict in liquidiation_values_across_accounts_dict.values()]
        currencies = sum(currencies, []) # flatten

        return list(set(currencies))

    def get_net_liquidation_value_across_accounts(self):
        ## returns a dict, accountid as keys, of dicts, currencies as keys
        account_summary_dict = self.ib_get_account_summary()
        accounts = account_summary_dict.keys()
        liquidiation_values_across_accounts_dict = dict([(account_id, self.get_liquidation_values_for_single_account(account_id))
                                         for account_id in accounts])

        return liquidiation_values_across_accounts_dict

    def get_liquidation_values_for_single_account(self, account_id):
        ## returns a dict, with currencies as keys
        account_summary_dict = self.ib_get_account_summary()
        return account_summary_dict[account_id]['NetLiquidation']


    def broker_get_contract_expiry_date(self, contract_object_with_ib_broker_config):
        """
        Return the exact expiry date for a given contract

        :param contract_object_with_ib_broker_config:  contract where instrument has ib metadata
        :return: YYYYMMDD str
        """
        specific_log = self.log.setup(instrument_code = contract_object_with_ib_broker_config.instrument_code,
                                      contract_date = contract_object_with_ib_broker_config.date)

        ibcontract = self.ib_futures_contract(contract_object_with_ib_broker_config)
        if ibcontract is missing_contract:
            specific_log.warn("Can't get contract expiry from IB for %s" % str(contract_object_with_ib_broker_config))
            return missing_contract

        expiry_date = ibcontract.lastTradeDateOrContractMonth

        return expiry_date


    # IB specific methods
    # Called by parent class generics

    def ib_submit_single_leg_market_order(self, contract_object_with_ib_data, trade, account):
        ibcontract = self.ib_futures_contract(contract_object_with_ib_data)
        if ibcontract is missing_contract:
            return missing_order
        ## account?!s
        ib_BS_str, ib_qty = resolveBS(trade)
        ib_order = MarketOrder(ib_BS_str, ib_qty)
        if account!='':
            ib_order.account = account
        trade = self.ib.placeOrder(ibcontract, ib_order)

        return trade

    def _get_generic_data_for_contract(self, ibcontract, log=None, bar_freq="D", whatToShow='TRADES'):
        """
        Get historical daily data

        :param contract_object_with_ib_broker_config: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """
        if log is None:
            log = self.log

        try:
            barSizeSetting, durationStr = get_barsize_and_duration_from_frequency(bar_freq)
        except Exception as exception:
            log.warn(exception.args[0])
            return pd.Series()

        if ibcontract is missing_contract:
            log.warn("Can't find price with valid IB contract")
            return pd.Series()

        price_data_raw = self.ib_get_historical_data(ibcontract, durationStr=durationStr,
                                                     barSizeSetting=barSizeSetting,
                                              whatToShow = whatToShow, log=log)

        price_data_as_df = price_data_raw[['open', 'high', 'low', 'close', 'volume']]
        price_data_as_df.columns = ['OPEN', 'HIGH', 'LOW', 'FINAL', 'VOLUME']
        date_index = [ib_timestamp_to_datetime(price_row) for price_row in price_data_raw['date']]
        price_data_as_df.index = date_index

        return price_data_as_df


    def ib_spotfx_contract(self, ccy1, ccy2="USD", log=arg_not_supplied):
        ibcontract = Forex(ccy1+ccy2)

        ibcontract = self.ib_resolve_unique_contract(ibcontract)

        return ibcontract

    def ib_futures_contract(self, futures_contract_object):
        """
        Return a complete and unique IB contract that matches futures_contract_object
        Doesn't actually get the data from IB, tries to get from cache

        :param futures_contract_object: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """

        if getattr(self, "_futures_contract_cache", None) is None:
            self._futures_contract_cache = {}

        cache = self._futures_contract_cache
        key = futures_contract_object.ident()

        ibcontract = cache.get(key, missing_contract)
        if ibcontract is missing_contract:
            ibcontract = self._get_ib_futures_contract(futures_contract_object)
            cache[key] = ibcontract

        return ibcontract


    def _get_ib_futures_contract(self, futures_contract_object):
        """
        Return a complete and unique IB contract that matches futures_contract_object
        This is expensive so not called directly, only by ib_futures_contract which does caching

        :param futures_contract_object: contract, containing instrument metadata suitable for IB
        :return: a single ib contract object
        """
        # Convert to IB world
        instrument_object_with_metadata = futures_contract_object.instrument
        ibcontract = ib_futures_instrument(instrument_object_with_metadata)

        # Register the contract to make logging and error handling cleaner
        self.add_contract_to_register(ibcontract,
                                      log_tags = dict(instrument_code = instrument_object_with_metadata.instrument_code,
                                                      contract_date = futures_contract_object.date))

        # The contract date might be 'yyyymm' or 'yyyymmdd'
        contract_day_passed = futures_contract_object.contract_date.is_day_defined()
        if contract_day_passed:
            ## Already have the expiry
            contract_date = futures_contract_object.contract_date
        else:
            ## Don't have the expiry so lose the days at the end so it's just 'YYYYMM'
            contract_date = str(futures_contract_object.contract_date)[:6]

        ibcontract.lastTradeDateOrContractMonth = contract_date

        ## We allow multiple contracts in case we have 'yyyymm' and not specified expiry date for VIX
        ibcontract_list = self.ib_get_contract_chain(ibcontract)

        if len(ibcontract_list)==0:
            ## No contracts found
            return missing_contract

        if len(ibcontract_list)==1:
            ## OK no hassle, only one contract no confusion
            resolved_contract = ibcontract_list[0]
        else:
            ## It might be a contract with weekly expiries (probably VIX)
            ## We need to find the right one
            try:
                resolved_contract = resolve_multiple_expiries(ibcontract_list, instrument_object_with_metadata)
            except Exception as exception:
                self.log.warn("%s could not resolve contracts: %s" %
                              (str(instrument_object_with_metadata), exception.args[0]))

                return missing_contract

        return resolved_contract


    def ib_resolve_unique_contract(self, ibcontract_pattern, log=None):
        """
        Returns the 'resolved' IB contract based on a pattern. We expect a unique contract.

        :param ibcontract_pattern: ibContract
        :param log: log object
        :return: ibContract or missing_contract
        """
        if log is None:
            log=self.log

        contract_chain = self.ib_get_contract_chain(ibcontract_pattern, log=log)

        if len(contract_chain) > 1:
            log.warn("Got multiple contracts for %s when only expected a single contract: Check contract date" % str(ibcontract_pattern))
            return missing_contract
        if len(contract_chain) == 0:
            log.warn("Failed to resolve contract %s" % str(ibcontract_pattern))
            return missing_contract

        resolved_contract = contract_chain[0]

        return resolved_contract

    def ib_get_contract_chain(self, ibcontract_pattern, log=None):
        """
        Get all the IB contracts matching a pattern.

        :param ibcontract_pattern: ibContract which may not fully specify the contract
        :param log: log object
        :return: list of ibContracts
        """

        if log is None:
            log=self.log

        new_contract_details_list = self.ib.reqContractDetails(ibcontract_pattern)

        ibcontract_list = [contract_details.contract for contract_details in new_contract_details_list]

        return ibcontract_list


    ## HISTORICAL DATA
    ## Works for FX and futures
    def ib_get_historical_data(self, ibcontract, durationStr="1 Y", barSizeSetting="1 day",
                               whatToShow = "TRADES", log=None):

        """
        Returns historical prices for a contract, up to today
        ibcontract is a Contract
        :returns list of prices in 4 tuples: Open high low close volume
        """

        if log is None:
            log = self.log

        last_call = self.last_historic_price_calltime
        avoid_pacing_violation(last_call, log=log)

        bars = self.ib.reqHistoricalData(
            ibcontract,
            endDateTime='',
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            useRTH=True,
            formatDate=1)
        df = util.df(bars)


        self.last_historic_price_calltime = datetime.datetime.now()

        return df

    def ib_get_account_summary(self):
        data_stale = self._ib_get_account_summary_if_cache_stale()
        if data_stale:
            account_summary_data =  self._ib_get_account_summary_if_cache_stale()
        else:
            account_summary_data = self._account_summary_data

        return account_summary_data

    def _ib_get_account_summary_check_for_stale_cache(self):
        account_summary_data_update = getattr(self, "_account_summary_data_update", None)
        account_summary_data = getattr(self, "_account_summary_data", None)

        if account_summary_data_update is None or account_summary_data is None:
            return True
        elapsed_seconds = (account_summary_data_update - datetime.datetime.now()).total_seconds()

        if elapsed_seconds>STALE_SECONDS_ALLOWED_ACCOUNT_SUMMARY:
            return True
        else:
            return False

    def _ib_get_account_summary_if_cache_stale(self):

        account_summary_rawdata = self.ib.accountSummary()

        ## Weird format let's clean it up
        account_summary_dict = clean_up_account_summary(account_summary_rawdata)

        self._account_summary_data = account_summary_dict
        self._account_summary_data_update = datetime.datetime.now()

        return account_summary_dict



def clean_up_account_summary(account_summary_rawdata):
    list_of_accounts = _unique_list_from_total(account_summary_rawdata, 'account')
    list_of_tags = _unique_list_from_total(account_summary_rawdata, 'tag')

    account_summary_dict = {}
    for account_id in list_of_accounts:
        account_summary_dict[account_id]={}
        for tag in list_of_tags:
            account_summary_dict[account_id][tag] = {}

    for account_item in account_summary_rawdata:
        try:
            value = float(account_item.value)
        except ValueError:
            value = account_item.value
        account_summary_dict[account_item.account][account_item.tag][account_item.currency] = value

    return account_summary_dict

def _unique_list_from_total(account_summary_data, tag_name):
    list_of_items = [getattr(account_value, tag_name) for account_value in account_summary_data]
    list_of_items = list(set(list_of_items))
    return list_of_items


def get_barsize_and_duration_from_frequency(bar_freq):

    barsize_lookup = dict([('D', "1 day"), ('H', "1 hour"), ('15M', '15 mins'), ('5M', '5 mins'), ('M', '1 min'),
                           ('10S', '10 secs'), ('S', '1 secs')])
    duration_lookup = dict([('D', "1 Y"), ('H', "1 M"), ('15M', '1 W'), ('5M', "1 W"), ('M', '1 D'),
                            ('10S', '14400 S'), ('S', '1800 S')])
    try:
        assert bar_freq in barsize_lookup.keys() and bar_freq in duration_lookup.keys()
    except:
        raise Exception("Barsize %s not recognised should be one of %s" % (bar_freq, str(barsize_lookup.keys())))

    ib_barsize = barsize_lookup[bar_freq]
    ib_duration = duration_lookup[bar_freq]

    return ib_barsize, ib_duration

def ib_futures_instrument(futures_instrument_object):
    """
    Get an IB contract which is NOT specific to a contract date
    Used for getting expiry chains

    :param futures_instrument_object: instrument with .metadata suitable for IB
    :return: IBcontract
    """

    meta_data = futures_instrument_object.meta_data

    ibcontract = Future(meta_data['symbol'], exchange = meta_data['exchange'])
    if meta_data['ibMultiplier'] is NOT_REQUIRED:
        pass
    else:
        ibcontract.multiplier = int(meta_data['ibMultiplier'])
    if meta_data['currency'] is NOT_REQUIRED:
        pass
    else:
        ibcontract.currency = meta_data['currency']

    return ibcontract


def resolve_multiple_expiries(ibcontract_list, instrument_object_with_metadata):
    code = instrument_object_with_metadata.instrument_code
    ignore_weekly = instrument_object_with_metadata.meta_data['ignoreWeekly']
    if not ignore_weekly:
        ## Can't be resolved
        raise Exception("%s has multiple plausible contracts but is not set to ignoreWeekly in IB config file" % code)

    ## It's a contract with weekly expiries (probably VIX)
    ## Check it's the VIX
    if not code=="VIX":
        raise Exception("You have specified weekly expiries, but I don't have logic for %s" % code)

    # Get the symbols
    contract_symbols = [ibcontract.localSymbol for ibcontract in ibcontract_list]
    try:
        are_monthly = [_is_vix_symbol_monthly(symbol) for symbol in contract_symbols]
    except Exception as exception:
        raise Exception(exception.args[0])

    if are_monthly.count(monthly):
        index_of_monthly = are_monthly.index(monthly)
        resolved_contract = ibcontract_list[index_of_monthly]
    else:
        # no matches or multiple matches
        raise Exception("Can't find a unique monthly expiry")

    return resolved_contract

monthly=object()
weekly=object()

def _is_vix_symbol_monthly(symbol):
    if re.match("VX[0-9][0-9][A-Z][0-9]", symbol):
        # weekly
        return weekly
    elif re.match("VX[A-Z][0-9]", symbol):
        # monthly
        return monthly
    else:
        raise Exception("IB Local Symbol %s not recognised" % symbol)

def avoid_pacing_violation(last_call_datetime, log=logtoscreen("")):
    printed_warning_already = False
    while (datetime.datetime.now() - last_call_datetime).total_seconds() < PACING_INTERVAL_SECONDS:
        if not printed_warning_already:
            log.msg(
                "Pausing %f seconds to avoid pacing violation" % (datetime.datetime.now() - last_call_datetime).total_seconds())
            printed_warning_already = True
        pass

def ib_timestamp_to_datetime(timestamp_ib):
    """
    Turns IB timestamp into pd.datetime as plays better with arctic, and adjusts yyyymm to closing vector

    :param timestamp_str: datetime.datetime
    :return: pd.datetime
    """
    timestamp = pd.to_datetime(timestamp_ib)

    adjusted_ts = adjust_timestamp(timestamp)

    return adjusted_ts

def from_ib_positions_to_dict(raw_positions):
    """

    :param raw_positions: list of positions in form Position(...)
    :return: dict of positions as dataframes
    """
    resolved_positions_dict = dict()
    position_methods = dict(STK = resolve_ib_stock_position, FUT = resolve_ib_future_position,
                            CASH = resolve_ib_cash_position)
    for position in raw_positions:
        asset_class = position.contract.secType
        method = position_methods.get(asset_class, None)
        if method is None:
            raise Exception("Can't find asset class %s in methods dict" % asset_class)

        resolved_position = method(position)
        asset_class_list = resolved_positions_dict.get(asset_class, [])
        asset_class_list.append(resolved_position)
        resolved_positions_dict[asset_class] = asset_class_list

    return resolved_positions_dict

def resolve_ib_stock_position(position):
    return dict(account = position.account, symbol = position.contract.symbol,
                multiplier = 1.0, expiry = "",
                exchange = position.contract.exchange, currency = position.contract.currency,
                position = position.position)

def resolve_ib_future_position(position):
    return dict(account = position.account, symbol = position.contract.symbol, expiry = position.contract.lastTradeDateOrContractMonth,
                multiplier = float(position.contract.multiplier), currency = position.contract.currency,
                position = position.position)

def resolve_ib_cash_position(position):
    return dict(account = position.account, symbol = position.contract.localSymbol,
                expiry = "", multiplier = 1.0,
                currency = position.contract.currency, position = position.position)

def resolveBS(trade):
    if trade<0:
        return 'SELL', abs(trade)
    return 'BUY', abs(trade)


def sign_from_BS(action):
    if action=="SELL":
        return -1
    return 1


def extract_trade_info(trade_to_process):
    order_info = extract_order_info(trade_to_process)
    contract_info = extract_contract_info(trade_to_process)
    fill_info = extract_fill_info(trade_to_process)

    algo_msg = " ".join([str(log_entry) for log_entry in trade_to_process.log])
    total_filled = trade_to_process.filled()
    active = trade_to_process.isActive()

    tradeInfo = namedtuple("tradeInfo", ['order', 'contract', 'fills','algo_msg', 'total_filled', 'active'])
    trade_info = tradeInfo(order_info, contract_info, fill_info, algo_msg, total_filled, active)

    return trade_info

def extract_order_info(trade_to_process):
    order = trade_to_process.order

    account = order.account
    perm_id = order.permId
    limit_price = order.lmtPrice
    order_sign = sign_from_BS(order.action)
    order_type = resolve_order_type(order.orderType)
    remain_qty = order.totalQuantity

    orderInfo = namedtuple('orderInfo', ['account',  'perm_id', 'limit_price', 'order_sign', 'type',
                                         'remain_qty'])
    order_info = orderInfo(account=account, perm_id=perm_id, limit_price=limit_price,
                order_sign=order_sign, type = order_type, remain_qty=remain_qty)

    return order_info

def extract_contract_info(trade_to_process):
    contract = trade_to_process.contract
    ib_instrument_code = contract.symbol
    ib_contract_id = contract.lastTradeDateOrContractMonth
    ib_sectype = contract.secType

    contractInfo = namedtuple("contractInfo", ['ib_instrument_code', 'ib_contract_id', 'ib_sectype'])
    contract_info = contractInfo(ib_instrument_code=ib_instrument_code, ib_contract_id=ib_contract_id,
                                 ib_sectype=ib_sectype)

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

