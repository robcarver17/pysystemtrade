import datetime
import pandas as pd
import re

from ib_insync import Forex, Future, util

from sysbrokers.baseClient import brokerClient
from syscore.genutils import NOT_REQUIRED
from syscore.objects import missing_contract, arg_not_supplied
from syscore.dateutils import adjust_timestamp
from syslogdiag.log import logtoscreen


MAX_WAIT_HISTORICAL_DATA_SECONDS = 30
_PACING_PERIOD_SECONDS = 10*60
_PACING_PERIOD_LIMIT = 60
PACING_INTERVAL_SECONDS = 1+(_PACING_PERIOD_SECONDS  / _PACING_PERIOD_LIMIT)


class ibClient(brokerClient):
    """
    Client specific to interactive brokers

    Overrides the methods in the base class specifically for IB

    """

    def __init__(self, log=logtoscreen("ibClient")):

        self.log = log
        ## means our first call won't be throttled for pacing
        self.last_historic_price_calltime = datetime.datetime.now()-  datetime.timedelta(seconds=_PACING_PERIOD_SECONDS)

    # Methods in parent class overriden here
    # These methods should abstract the broker completely
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



    # Broker specific methods
    # Called by parent class generics
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



def get_barsize_and_duration_from_frequency(bar_freq):

    barsize_lookup = dict([('D', "1 day"), ('H', "1 hour"), ('5M', '5 mins'), ('M', '1 min'),
                           ('10S', '10 secs'), ('S', '1 secs')])
    duration_lookup = dict([('D', "1 Y"), ('H', "1 M"), ('5M', "1 W"), ('M', '1 D'),
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

