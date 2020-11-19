#FIXME HAS A LOT OF IMPORTS - SPLIT THINGS OUT?

import pandas as pd
from syscore.objects import missing_data, missing_contract

from sysbrokers.IB.ib_futures_contracts_data import ibFuturesContractData
from sysbrokers.IB.ib_instruments_data import ibFuturesInstrumentData
from sysbrokers.IB.ib_translate_broker_order_objects import sign_from_BS, ibBrokerOrder
from sysdata.futures.futures_per_contract_prices import (
    futuresContractPriceData,
)
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.contracts import futuresContract, listOfFuturesContracts

from sysexecution.tick_data import tickerObject
from sysexecution.contract_orders import contractOrder

from syslogdiag.log import logtoscreen


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


def from_ib_bid_ask_tick_data_to_dataframe(tick_data) ->pd.DataFrame:
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



class ibFuturesContractPriceData(futuresContractPriceData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This gets HISTORIC data from interactive brokers. It is blocking code
    In a live production system it is suitable for running on a daily basis to get end of day prices

    """

    def __init__(self, ibconnection, log=logtoscreen(
            "ibFuturesContractPriceData")):
        self._ibconnection = ibconnection
        super().__init__(log=log)

    def __repr__(self):
        return "IB Futures per contract price data %s" % str(self.ibconnection)

    @property
    def log(self):
        return self._log

    @property
    def ibconnection(self):
        return self._ibconnection

    @property
    def futures_contract_data(self):
        return ibFuturesContractData(self.ibconnection, log = self.log)

    @property
    def futures_instrument_data(self):
        return ibFuturesInstrumentData(self.ibconnection, log = self.log)

    def has_data_for_contract(self, contract_object: futuresContract):
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

    def get_list_of_instrument_codes_with_price_data(self) -> list:
        list_of_instruments = self.futures_instrument_data.get_list_of_instruments()

        return list_of_instruments

    def contracts_with_price_data_for_instrument_code(self, instrument_code: str) -> listOfFuturesContracts:
        futures_instrument_with_ib_data = self.futures_instrument_data.get_futures_instrument_object_with_IB_data(instrument_code)
        list_of_date_str = self.ibconnection.broker_get_futures_contract_list(futures_instrument_with_ib_data)

        list_of_contracts = [futuresContract(instrument_code, date_str) for date_str in list_of_date_str]

        list_of_contracts = listOfFuturesContracts(list_of_contracts)

        return list_of_contracts

    def get_contracts_with_price_data(self):
        raise NotImplementedError(
            "Do not use get_contracts_with_price_data with IB")


    def _get_prices_for_contract_object_no_checking(self, contract_object: futuresContract) -> futuresContractPrices:
        return self._get_prices_at_frequency_for_contract_object_no_checking(
            contract_object, freq="D"
        )

    def _get_prices_at_frequency_for_contract_object_no_checking(self, contract_object: futuresContract,
                                                                 freq: str
                                                    ) -> futuresContractPrices:

        """
        Get historical prices at a particular frequency

        We override this method, rather than _get_prices_at_frequency_for_contract_object_no_checking
        Because the list of dates returned by contracts_with_price_data is likely to not match (expiries)

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 15M, 5M, M, 10S, S
        :return: data
        """
        new_log = contract_object.log(self.log)

        contract_object_with_ib_broker_config = (
            self.futures_contract_data.get_contract_object_with_IB_data(
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
            price_data = futuresContractPrices.create_empty()
        else:
            price_data = futuresContractPrices(price_data)

        price_data = price_data.remove_future_data()
        price_data = price_data.remove_zero_volumes()

        return price_data


    def _write_prices_for_contract_object_no_checking(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def delete_prices_for_contract_object(self, *args, **kwargs):
        raise NotImplementedError("IB is a read only source of prices")

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object: futuresContract
    ):
        raise NotImplementedError("IB is a read only source of prices")


    def get_recent_bid_ask_tick_data_for_order(self, order: contractOrder):
        ans = self._perform_contract_method_for_order(
            order, "get_recent_bid_ask_tick_data_for_contract_object"
        )
        return ans

    def get_ticker_object_for_order(self, order: contractOrder) -> tickerObject:
        ans = self._perform_contract_method_for_order(
            order, "get_ticker_object_for_contract_object"
        )
        return ans

    def cancel_market_data_for_order(self, order: ibBrokerOrder):
        ans = self._perform_contract_method_for_order(
            order, "cancel_market_data_for_contract_object"
        )
        return ans

    def _perform_contract_method_for_order(self, order, method, **kwargs):
        contract_object = futuresContract(
            order.instrument_code, order.contract_id)
        trade_list_for_multiple_legs = order.trade.qty
        method_to_call = getattr(self, method)

        result = method_to_call(
            contract_object,
            trade_list_for_multiple_legs=trade_list_for_multiple_legs,
            **kwargs
        )

        return result


    def get_ticker_object_for_contract_object(
        self, contract_object: futuresContract, trade_list_for_multiple_legs=None) -> ibTickerObject:

        """
        Returns my encapsulation of a ticker object

        :param contract_object:
        :param trade_list_for_multiple_legs:
        :return:
        """

        new_log = contract_object.log(self.log)

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_data(contract_object)
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
        self, contract_object: futuresContract, trade_list_for_multiple_legs=None
    ):
        """
        Returns my encapsulation of a ticker object

        :param contract_object:
        :param trade_list_for_multiple_legs:
        :return:
        """

        new_log = contract_object.log(self.log)

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_data(
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
    ) ->pd.DataFrame:
        """
        Get last few price ticks

        :param contract_object: futuresContract
        :return:
        """
        new_log = contract_object.log(self.log)

        contract_object_with_ib_data = (
            self.futures_contract_data.get_contract_object_with_IB_data(
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


