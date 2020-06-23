import datetime
import pandas as pd



from ib_insync import Forex,  util
from ib_insync.order import MarketOrder

from sysdata.fx.spotfx import currencyValue
from sysbrokers.baseClient import brokerClient

from syscore.objects import missing_contract, arg_not_supplied, missing_order
from syscore.dateutils import adjust_timestamp
from syslogdiag.log import logtoscreen

from sysbrokers.IB.ib_trading_hours import get_trading_hours
from sysbrokers.IB.ib_contracts import ib_futures_instrument, resolve_multiple_expiries
from sysbrokers.IB.ib_positions import from_ib_positions_to_dict, resolveBS

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

        return trades_in_broker_format

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
            raw_trade_object = self.ib_submit_single_leg_market_order(contract_object_with_ib_data, trade, account)
        else:
            self.log.critical("Order type %s is not supported for order on %s" % (order_type, str(contract_object_with_ib_data)))
            return missing_order

        return raw_trade_object

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

    def ib_get_recent_bid_ask_tick_data(self, contract_object_with_ib_broker_config, tick_count = 200):
        """

        :param contract_object_with_ib_broker_config:
        :return:
        """
        specific_log = self.log.setup(instrument_code = contract_object_with_ib_broker_config.instrument_code,
                                      contract_date = contract_object_with_ib_broker_config.date)

        ibcontract = self.ib_futures_contract(contract_object_with_ib_broker_config)
        if ibcontract is missing_contract:
            specific_log.warn("Can't find matching IB contract for %s" % str(contract_object_with_ib_broker_config))
            return missing_contract
        recent_ib_time = self.ib.reqCurrentTime() - datetime.timedelta(seconds=60)

        tick_data = self.ib.reqHistoricalTicks(ibcontract, recent_ib_time, '', tick_count, 'BID_ASK', useRth=False)

        return tick_data

    def ib_get_trading_hours(self, contract_object_with_ib_broker_config):
        ib_contract = self.ib_futures_contract(contract_object_with_ib_broker_config)
        if ib_contract is missing_contract:
            return missing_contract

        ib_contract_details = self.ib.reqContractDetails(ib_contract)[0]

        try:
            trading_hours = get_trading_hours(ib_contract_details)
        except Exception as e:
            self.log.critical("%s when getting trading hours!" % e)
            return missing_contract


        return trading_hours

    def ib_modify_existing_order(self, modified_order_object, original_contract_object):
        new_trade_object = self.ib.placeOrder(original_contract_object, modified_order_object)

        return new_trade_object

    def ib_cancel_order(self, original_order_object):
        new_trade_object = self.ib.cancelOrder(original_order_object)

        return new_trade_object

    def ib_check_order_is_cancelled(self, original_order_object):
        return original_order_object.OrderStatus == 'Cancelled'

    def ib_submit_single_leg_market_order(self, contract_object_with_ib_data, trade, account=""):
        ibcontract = self.ib_futures_contract(contract_object_with_ib_data)
        if ibcontract is missing_contract:
            return missing_order

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
