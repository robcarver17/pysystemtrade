import pandas as pd
import datetime
from syscore.fileutils import get_filename_for_package
from syscore.genutils import value_or_npnan, NOT_REQUIRED
from syscore.objects import missing_data, missing_contract

from sysbrokers.IB.ib_futures_contracts import ibFuturesContractData
from sysbrokers.IB.ib_translate_broker_order_objects import sign_from_BS
from sysdata.futures.futures_per_contract_prices import (
    futuresContractPriceData,
    futuresContractPrices,
)
from sysobjects.instruments import futuresInstrument

from sysexecution.tick_data import tickerObject, oneTick

from syslogdiag.log import logtoscreen

IB_FUTURES_CONFIG_FILE = get_filename_for_package(
    "sysbrokers.IB.ib_config_futures.csv")


class ibFuturesContractPriceData(futuresContractPriceData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        setattr(self, "ibconnection", ibconnection)
        setattr(self, "log", log)

    def __repr__(self):
        return "IB Futures per contract price data %s" % str(self.ibconnection)

    @property
    def futures_contract_data(self):
        return ibFuturesContractData(self.ibconnection)

    def has_data_for_contract(self, contract_object):
        """
        Does IB have data for a given contract?

        Overriden because we will have a problem matching expiry dates to nominal yyyymm dates
        :param contract_object:
        :return: bool
        """
        expiry_date = self.futures_contract_data.get_actual_expiry_date_for_contract(
            contract_object)
        if expiry_date is missing_contract:
            return False
        else:
            return True

    def get_instruments_with_price_data(self):
        """
        Get instruments that have price data
        Pulls these in from a config file

        :return: list of str
        """

        return self.futures_contract_data.get_instruments_with_config_data()

    def get_prices_for_contract_object(self, contract_object):
        """
        Get some prices
        (daily frequency: using IB historical data)

        :param contract_object:  futuresContract
        :return: data
        """

        return self.get_prices_at_frequency_for_contract_object(
            contract_object, freq="D"
        )

    def get_prices_at_frequency_for_contract_object(
            self, contract_object, freq="D"):
        """
        Get historical prices at a particular frequency

        We override this method, rather than _get_prices_at_frequency_for_contract_object_no_checking
        Because the list of dates returned by contracts_with_price_data is likely to not match (expiries)

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 15M, 5M, M, 10S, S
        :return: data
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_broker_config = (
            self.futures_contract_data.get_contract_object_with_IB_metadata(
                contract_object
            )
        )
        if contract_object_with_ib_broker_config is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        price_data = self.ibconnection.broker_get_historical_futures_data_for_contract(
            contract_object_with_ib_broker_config, bar_freq=freq)

        if len(price_data) == 0:
            new_log.warn(
                "No IB price data found for %s" %
                str(contract_object))
            data = futuresContractPrices.create_empty()
        else:
            data = futuresContractPrices(price_data)

        data = futuresContractPrices(
            data[data.index < datetime.datetime.now()])
        data = data.remove_zero_volumes()

        return data

    def get_ticker_object_for_contract_object(
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        """
        Returns my encapsulation of a ticker object

        :param contract_object:
        :param trade_list_for_multiple_legs:
        :return:
        """

        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_metadata(
                contract_object
            )
        )
        if contract_object_with_ib_data is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        ticker_with_bs = self.ibconnection.get_ticker_object(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )

        ticker_object = ibTickerObject(ticker_with_bs, self.ibconnection)

        return ticker_object

    def cancel_market_data_for_contract_object(
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        """
        Returns my encapsulation of a ticker object

        :param contract_object:
        :param trade_list_for_multiple_legs:
        :return:
        """

        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_metadata(
                contract_object
            )
        )
        if contract_object_with_ib_data is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        self.ibconnection.cancel_market_data_for_contract_object(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )

    def get_recent_bid_ask_tick_data_for_contract_object(
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        """
        Get last few price ticks

        :param contract_object: futuresContract
        :return:
        """
        new_log = self.log.setup(
            instrument_code=contract_object.instrument_code,
            contract_date=contract_object.date,
        )

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_metadata(
                contract_object
            )
        )
        if contract_object_with_ib_data is missing_contract:
            new_log.warn("Can't get data for %s" % str(contract_object))
            return futuresContractPrices.create_empty()

        tick_data = self.ibconnection.ib_get_recent_bid_ask_tick_data(
            contract_object_with_ib_data,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
        )
        if tick_data is missing_contract:
            return missing_data

        tick_data_as_df = from_ib_bid_ask_tick_data_to_dataframe(tick_data)

        return tick_data_as_df

    def _get_prices_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError(
            "_get_prices_for_contract_object_no_checking should not be called for IB type object"
        )

    def _get_prices_at_frequency_for_contract_object_no_checking(
            self, *args, **kwargs):
        raise NotImplementedError(
            "_get_prices_at_frequency_for_contract_object_no_checking should not be called for IB type object"
        )

    def _write_prices_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def delete_prices_for_contract_object(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def get_contracts_with_price_data(self, *args, **kwargs):
        raise NotImplementedError(
            "Do not use get_contracts_with_price_data with IB")


class ibTickerObject(tickerObject):
    def __init__(self, ticker_with_BS, broker_connection):
        ticker = ticker_with_BS.ticker
        BorS = ticker_with_BS.BorS
        qty = sign_from_BS(BorS)
        super().__init__(ticker, qty=qty)
        self._broker_connection = broker_connection

    def refresh(self):
        self._broker_connection.refresh()

    def bid(self):
        return self.ticker.bid

    def ask(self):
        return self.ticker.ask

    def bid_size(self):
        return self.ticker.bidSize

    def ask_size(self):
        return self.ticker.askSize


def from_ib_bid_ask_tick_data_to_dataframe(tick_data):
    """

    :param tick_data: list of HistoricalTickBidAsk()
    :return: pd.DataFrame,['priceBid', 'priceAsk', 'sizeAsk', 'sizeBid']
    """
    time_index = [tick_item.time for tick_item in tick_data]
    fields = ["priceBid", "priceAsk", "sizeAsk", "sizeBid"]

    value_dict = {}
    for field_name in fields:
        field_values = [getattr(tick_item, field_name)
                        for tick_item in tick_data]
        value_dict[field_name] = field_values

    output = pd.DataFrame(value_dict, time_index)

    return output
