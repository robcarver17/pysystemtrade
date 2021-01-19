from dateutil.tz import tz

import  datetime
import pandas as pd

from ib_insync import Contract as ibContract
from ib_insync import util

from sysbrokers.IB.client.ib_client import ibClient, PACING_INTERVAL_SECONDS
from sysbrokers.IB.client.ib_contracts_client import ibContractsClient
from sysbrokers.IB.ib_positions import (
    from_ib_positions_to_dict,
    resolveBS,
    resolveBS_for_list,
positionsFromIB
)
from syscore.objects import missing_contract, missing_data
from syscore.dateutils import adjust_timestamp_to_include_notional_close_and_time_offset, strip_timezone_fromdatetime

from syslogdiag.log import logger, logtoscreen

from sysobjects.contracts import futuresContract


class tickerWithBS(object):
    def __init__(self, ticker, BorS):
        self.ticker = ticker
        self.BorS = BorS

# we don't include ibClient since we get that through contracts client
class ibPriceClient(ibContractsClient):
    def broker_get_historical_futures_data_for_contract(
        self, contract_object_with_ib_broker_config: futuresContract, bar_freq="D"
    ) -> pd.Series:
        """
        Get historical daily data

        :param contract_object_with_ib_broker_config: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """

        specific_log = contract_object_with_ib_broker_config.specific_log(self.log)

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_broker_config)
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't resolve IB contract %s"
                % str(contract_object_with_ib_broker_config)
            )
            return missing_data

        price_data = self._get_generic_data_for_contract(
            ibcontract, log=specific_log, bar_freq=bar_freq, whatToShow="TRADES")

        return price_data

    def get_ticker_object(
        self, contract_object_with_ib_data: futuresContract, trade_list_for_multiple_legs=None
    ) -> tickerWithBS:

        specific_log = contract_object_with_ib_data.specific_log(self.log)

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract

        self.ib.reqMktData(ibcontract, "", False, False)
        ticker = self.ib.ticker(ibcontract)

        ib_BS_str, ib_qty = resolveBS_for_list(trade_list_for_multiple_legs)

        ticker_with_bs = tickerWithBS(ticker, ib_BS_str)

        return ticker_with_bs

    def cancel_market_data_for_contract_object(
        self, contract_object_with_ib_data: futuresContract, trade_list_for_multiple_legs=None
    ):

        specific_log = contract_object_with_ib_data.specific_log(self.log)

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract

        self.ib.cancelMktData(ibcontract)

    def ib_get_recent_bid_ask_tick_data(
        self,
        contract_object_with_ib_data: futuresContract,
        trade_list_for_multiple_legs=None,
        tick_count=200,
    ):
        """

        :param contract_object_with_ib_data:
        :return:
        """
        specific_log = self.log.setup(
            instrument_code=contract_object_with_ib_data.instrument_code,
            contract_date=contract_object_with_ib_data.date_str,
        )
        if contract_object_with_ib_data.is_spread_contract():
            raise Exception("Can't get historical data for combo")

        ibcontract = self.ib_futures_contract(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if ibcontract is missing_contract:
            specific_log.warn(
                "Can't find matching IB contract for %s"
                % str(contract_object_with_ib_data)
            )
            return missing_contract
        recent_ib_time = self.ib.reqCurrentTime() - datetime.timedelta(seconds=60)

        tick_data = self.ib.reqHistoricalTicks(
            ibcontract, recent_ib_time, "", tick_count, "BID_ASK", useRth=False
        )

        return tick_data


    def _get_generic_data_for_contract(
        self, ibcontract: ibContract,
                          log:logger=None,
                                     bar_freq: str="D",
                                                   whatToShow:str="TRADES"
    ) -> pd.Series:
        """
        Get historical daily data

        :param contract_object_with_ib_data: contract where instrument has ib metadata
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: futuresContractPriceData
        """
        if log is None:
            log = self.log

        if ibcontract is missing_contract:
            log.warn("Can't find price with valid IB contract")
            return missing_data

        try:
            barSizeSetting, durationStr = get_barsize_and_duration_from_frequency(
                bar_freq)
        except Exception as exception:
            log.warn(str(exception.args[0]))
            return missing_data

        price_data_raw = self.ib_get_historical_data(
            ibcontract,
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            log=log,
        )

        if price_data_raw is None:
            log.warn("No price data from IB")
            return missing_data

        price_data_as_df = price_data_raw[[
            "open", "high", "low", "close", "volume"]]
        price_data_as_df.columns = ["OPEN", "HIGH", "LOW", "FINAL", "VOLUME"]
        date_index = [
            self.ib_timestamp_to_datetime(price_row)
            for price_row in price_data_raw["date"]
        ]
        price_data_as_df.index = date_index

        return price_data_as_df

    ### TIMEZONE STUFF
    def ib_timestamp_to_datetime(self, timestamp_ib):
        """
        Turns IB timestamp into pd.datetime as plays better with arctic, converts IB time (UTC?) to local,
        and adjusts yyyymm to closing vector

        :param timestamp_str: datetime.datetime
        :return: pd.datetime
        """

        local_timestamp_ib = self.adjust_ib_time_to_local(timestamp_ib)
        timestamp = pd.to_datetime(local_timestamp_ib)

        adjusted_ts = adjust_timestamp_to_include_notional_close_and_time_offset(timestamp)

        return adjusted_ts

    def adjust_ib_time_to_local(self, timestamp_ib):

        if getattr(timestamp_ib, "tz_localize", None) is None:
            # daily, nothing to do
            return timestamp_ib

        timestamp_ib_with_tz = self.add_tz_to_ib_time(timestamp_ib)
        local_timestamp_ib_with_tz = timestamp_ib_with_tz.astimezone(
            tz.tzlocal())
        local_timestamp_ib = strip_timezone_fromdatetime(local_timestamp_ib_with_tz)

        return local_timestamp_ib

    def add_tz_to_ib_time(self, timestamp_ib):
        ib_tz = self.get_ib_timezone()
        timestamp_ib_with_tz = timestamp_ib.tz_localize(ib_tz)

        return timestamp_ib_with_tz

    def get_ib_timezone(self):
        # cache
        ib_tz = getattr(self, "_ib_time_zone", None)
        if ib_tz is None:
            ib_time = self.ib.reqCurrentTime()
            ib_tz = ib_time.timetz().tzinfo
            self._ib_time_zone = ib_tz

        return ib_tz


    # HISTORICAL DATA
    # Works for FX and futures
    def ib_get_historical_data(
        self,
        ibcontract,
        durationStr="1 Y",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        log=None,
    ):
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
            endDateTime="",
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow=whatToShow,
            useRTH=True,
            formatDate=1,
        )
        df = util.df(bars)

        self.last_historic_price_calltime = datetime.datetime.now()

        return df

def get_barsize_and_duration_from_frequency(bar_freq):

    barsize_lookup = dict(
        [
            ("D", "1 day"),
            ("H", "1 hour"),
            ("15M", "15 mins"),
            ("5M", "5 mins"),
            ("M", "1 min"),
            ("10S", "10 secs"),
            ("S", "1 secs"),
        ]
    )
    duration_lookup = dict(
        [
            ("D", "1 Y"),
            ("H", "1 M"),
            ("15M", "1 W"),
            ("5M", "1 W"),
            ("M", "1 D"),
            ("10S", "14400 S"),
            ("S", "1800 S"),
        ]
    )
    try:
        assert bar_freq in barsize_lookup.keys() and bar_freq in duration_lookup.keys()
    except BaseException:
        raise Exception(
            "Barsize %s not recognised should be one of %s"
            % (bar_freq, str(barsize_lookup.keys()))
        )

    ib_barsize = barsize_lookup[bar_freq]
    ib_duration = duration_lookup[bar_freq]

    return ib_barsize, ib_duration



def avoid_pacing_violation(last_call_datetime, log=logtoscreen("")):
    printed_warning_already = False
    while (
        datetime.datetime.now() - last_call_datetime
    ).total_seconds() < PACING_INTERVAL_SECONDS:
        if not printed_warning_already:
            log.msg("Pausing %f seconds to avoid pacing violation" %
                    (datetime.datetime.now() - last_call_datetime).total_seconds())
            printed_warning_already = True
        pass


