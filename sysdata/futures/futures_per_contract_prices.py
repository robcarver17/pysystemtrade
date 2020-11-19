from syscore.objects import data_error

from sysobjects.contracts import futuresContract, listOfFuturesContracts
from sysobjects.futures_per_contract_prices import futuresContractPrices
from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractPrices

from syslogdiag.log import logtoscreen

BASE_CLASS_ERROR = "You have used a base class for futures price data; you need to use a class that inherits with a specific data source"

## REDUCE USE OF CODE/DATE STRING CALLS...
## SPLIT OUT SOMEWHAT?
## TICKER OBJECTS ETC DO THEY REALLY NEED TO BE HERE, AS NOT USED EXCEPT IN BROKER INHERITANCE?


class futuresContractPriceData(object):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This would normally be extended further for information from a specific source eg quandl, arctic

    Access via: object.get_prices_for_instrumentCode_and_contractDate('EDOLLAR','201702']
     or object.get_prices_for_contract_object(futuresContract(....))
    """

    def __init__(self, log=logtoscreen("futuresContractPriceData")):
        setattr(self, "_log", log)

    @property
    def log(self):
        return self._log

    def __repr__(self):
        return "Individual futures contract price data - DO NOT USE"

    def __getitem__(self, contract_object: futuresContract):
        """
        convenience method to get the price, make it look like a dict

        """

        return self.get_prices_for_contract_object(contract_object)

    def keys(self):
        """
        list of things in this data set (futures contracts, instruments...)

        :returns: list of str

        """
        return self.get_contracts_with_price_data()

    def get_contracts_with_price_data(self) ->listOfFuturesContracts:
        """

        :return: list of futuresContact
        """
        raise NotImplementedError(BASE_CLASS_ERROR)

    def get_list_of_instrument_codes_with_price_data(self)->list:
        """

        :return: list of str
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        unique_list_of_instruments = list_of_contracts_with_price_data.unique_list_of_instrument_codes()

        return unique_list_of_instruments


    def has_data_for_contract(self, contract_object: futuresContract) ->bool:
        list_of_contracts = self.get_contracts_with_price_data()
        if contract_object in list_of_contracts:
            return True
        else:
            return False

    def contracts_with_price_data_for_instrument_code(self, instrument_code):
        """
        Valid contracts

        :param instrument_code: str
        :return: list of contract_date
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        list_of_contracts_for_instrument = \
            list_of_contracts_with_price_data.contracts_with_price_data_for_instrument_code(instrument_code)

        return list_of_contracts_for_instrument

    def contract_dates_with_price_data_for_instrument_code(
            self, instrument_code):
        """

        :param instrument_code:
        :return: list of str
        """

        list_of_contracts_with_price_data = (
            self.contracts_with_price_data_for_instrument_code(instrument_code)
        )

        contract_dates = [
            str(contract.date_str)
            for contract in list_of_contracts_with_price_data
        ]

        return contract_dates




    def get_all_prices_for_instrument(self, instrument_code: str) ->dictFuturesContractPrices:
        """
        Get all the prices for this code, returned as dict

        :param instrument_code: str
        :return: dictFuturesContractPrices
        """

        list_of_contracts = self.contracts_with_price_data_for_instrument_code(instrument_code)
        dict_of_prices = dictFuturesContractPrices(
            [
                (
                    contract.date_str,
                    self.get_prices_for_contract_object(contract),
                )
                for contract in list_of_contracts
            ]
        )

        return dict_of_prices

    ## WHERE USED - TRY AND REMOVE
    def get_prices_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(
            instrument_code, contract_date, "get_prices_for_contract_object")

        return ans


    ### MOVE
    def get_recent_bid_ask_tick_data_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date
    ):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(
            instrument_code,
            contract_date,
            "get_recent_bid_ask_tick_data_for_contract_object",
        )

        return ans

    ## MOVE
    def get_recent_bid_ask_tick_data_for_order(self, order):
        ans = self._perform_contract_method_for_order(
            order, "get_recent_bid_ask_tick_data_for_contract_object"
        )
        return ans

    def get_ticker_object_for_order(self, order):
        ans = self._perform_contract_method_for_order(
            order, "get_ticker_object_for_contract_object"
        )
        return ans

    def cancel_market_data_for_order(self, order):
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
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        raise NotImplementedError

    def cancel_market_data_for_contract_object(
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        raise NotImplementedError

    def get_recent_bid_ask_tick_data_for_contract_object(
        self, contract_object, trade_list_for_multiple_legs=None
    ):
        raise NotImplementedError

    def get_prices_for_contract_object(self, contract_object):
        """
        get some prices

        :param contract_object:  futuresContract
        :return: data
        """

        if self.has_data_for_contract(contract_object):
            return self._get_prices_for_contract_object_no_checking(
                contract_object)
        else:
            return futuresContractPrices.create_empty()

    ## WHERE USED MOVE
    def get_prices_at_frequency_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date, freq="D"
    ):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :param freq: str; one of D, H, M5, M, 10S, S
        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(
            instrument_code,
            contract_date,
            "get_prices_at_frequency_for_contract_object",
            freq=freq,
        )

        return ans

    def get_prices_at_frequency_for_contract_object(
            self, contract_object, freq="D"):
        """
        get some prices

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: data
        """

        if self.has_data_for_contract(contract_object):
            return self._get_prices_at_frequency_for_contract_object_no_checking(
                contract_object, freq=freq)
        else:
            return futuresContractPrices.create_empty()

    def _get_prices_at_frequency_for_contract_object_no_checking(
        self, contract_object, freq
    ):
        """
        get some prices

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: data
        """

        raise NotImplementedError(BASE_CLASS_ERROR)

    def _get_prices_for_contract_object_no_checking(self, contract_object):
        """
        get some prices

        :param contract_object:  futuresContract
        :return: data
        """

        raise NotImplementedError(BASE_CLASS_ERROR)

    ## WHERE USED MOVE
    def write_prices_for_instrument_code_and_contract_date(
        self,
        instrument_code,
        contract_date,
        futures_price_data,
        ignore_duplication=False,
    ):
        """
        Write some prices

        :param futures_price_data:
        :param ignore_duplication: bool, to stop us overwriting existing prices
        :return: None
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(
            instrument_code,
            contract_date,
            "write_prices_for_contract_object",
            futures_price_data,
            ignore_duplication=ignore_duplication,
        )

        return ans

    def write_prices_for_contract_object(
            self,
            futures_contract_object,
            futures_price_data,
            ignore_duplication=False):
        """
        Write some prices

        :param futures_contract_object:
        :param futures_price_data:
        :param ignore_duplication: bool, to stop us overwriting existing prices
        :return: None
        """

        if self.has_data_for_contract(futures_contract_object):
            if ignore_duplication:
                pass
            else:
                self.log.warn(
                    "There is already existing data, you have to delete it first",
                    instrument_code=futures_contract_object.instrument_code,
                    contract_date=futures_contract_object.date_str
                )
                return None

        self._write_prices_for_contract_object_no_checking(
            futures_contract_object, futures_price_data
        )

    def _write_prices_for_contract_object_no_checking(
        self, futures_contract_object, futures_price_data
    ):
        """
        Write some prices

        We don't check to see if we've already written some, so only call directly with care
        :param futures_contract_object:
        :param futures_price_data:
        :return: None
        """

        raise NotImplementedError(BASE_CLASS_ERROR)

    ## MOVE
    def get_brokers_instrument_code(self, instrument_code):
        raise NotImplementedError(BASE_CLASS_ERROR)

    ## WHERE USED REMOVE
    def update_prices_for_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date, new_futures_per_contract_prices
    ):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :new futures prices: futuresPrices object
        :return: int, number of rows added
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(
            instrument_code,
            contract_date,
            "update_prices_for_contract",
            new_futures_per_contract_prices=new_futures_per_contract_prices,
        )

        return ans

    def update_prices_for_contract(
        self,
        futures_contract_object,
        new_futures_per_contract_prices,
        check_for_spike=True,
    ):
        """
        Reads existing data, merges with new_futures_prices, writes merged data

        :param new_futures_prices:
        :return: int, number of rows
        """
        new_log = self.log.setup(
            instrument_code=futures_contract_object.instrument_code,
            contract_date=futures_contract_object.date_str,
        )

        old_prices = self.get_prices_for_contract_object(
            futures_contract_object)
        merged_prices = old_prices.add_rows_to_existing_data(
            new_futures_per_contract_prices, check_for_spike=check_for_spike
        )

        if merged_prices is data_error:
            new_log.msg(
                "Price has moved too much - will need to manually check")
            return data_error

        rows_added = len(merged_prices) - len(old_prices)

        if rows_added == 0:
            if len(old_prices) == 0:
                new_log.msg("No existing or additional data")
                return 0
            else:
                new_log.msg("No additional data since %s " %
                        str(old_prices.index[-1]))
            return 0

        # We have guaranteed no duplication
        self.write_prices_for_contract_object(
            futures_contract_object, merged_prices, ignore_duplication=True
        )

        new_log.msg("Added %d additional rows of data" % rows_added)

        return rows_added

    ## ARE THESE DELETION METHODS ACTUALL USED??
    def _delete_all_prices_for_all_instruments(self, are_you_sure=False):
        if are_you_sure:
            instrument_list = self.get_list_of_instrument_codes_with_price_data()
            for instrument_code in instrument_list:
                self.delete_all_prices_for_instrument_code(
                    instrument_code, areyousure=are_you_sure
                )
        else:
            self.log.error(
                "You need to call delete_all_prices_for_all_instruments with a flag to be sure"
            )

    def delete_prices_for_contract_object(
        self, futures_contract_object, areyousure=False
    ):
        """

        :param futures_contract_object:
        :return:
        """

        if not areyousure:
            raise Exception(
                "You have to be sure to delete prices_for_contract_object!")

        if self.has_data_for_contract(futures_contract_object):
            self._delete_prices_for_contract_object_with_no_checks_be_careful(
                futures_contract_object
            )
        else:
            self.log.warn("Tried to delete non existent contract")

    def delete_all_prices_for_instrument_code(
            self, instrument_code, areyousure=False):
        # We don't pass areyousure, otherwise if we weren't sure would get
        # multiple exceptions
        if not areyousure:
            raise Exception(
                "You have to be sure to delete_all_prices_for_instrument!")

        all_contracts_to_delete = self.contracts_with_price_data_for_instrument_code(
            instrument_code)
        for contract in all_contracts_to_delete:
            self.delete_prices_for_contract_object(contract, areyousure=True)

    def _delete_prices_for_contract_object_with_no_checks_be_careful(
        self, futures_contract_object
    ):
        raise NotImplementedError(BASE_CLASS_ERROR)

    ## AIM TO EVENTUALLY REMOVE
    def _perform_contract_method_for_instrument_code_and_contract_date(
        self, instrument_code, contract_date, method_name, *args, **kwargs
    ):
        contract_object = self._object_given_instrumentCode_and_contractDate(
            instrument_code, contract_date
        )
        method = getattr(self, method_name)

        return method(contract_object, *args, **kwargs)

    def _object_given_instrumentCode_and_contractDate(
        self, instrument_code, contract_date
    ):
        """
        Quickly go from eg "EDOLLAR" "201801" to an object

        :param instrument_code: str
        :param contract_date: str
        :return: futuresContract
        """

        contract_object = futuresContract(instrument_code, contract_date)

        return contract_object
