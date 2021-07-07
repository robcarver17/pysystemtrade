import  datetime

from syscore.objects import missing_contract, arg_not_supplied, missing_data
from syscore.dateutils import Frequency, from_config_frequency_to_frequency

from sysobjects.contracts import futuresContract
from sysobjects.dict_of_futures_per_contract_prices import dictFuturesContractPrices, \
    get_last_matched_date_and_prices_for_contract_list
from sysobjects.spreads import spreadsForInstrument

from sysdata.arctic.arctic_futures_per_contract_prices import arcticFuturesContractPriceData, futuresContractPrices
from sysdata.arctic.arctic_multiple_prices import arcticFuturesMultiplePricesData, futuresMultiplePrices
from sysdata.arctic.arctic_adjusted_prices import arcticFuturesAdjustedPricesData, futuresAdjustedPrices
from sysdata.arctic.arctic_spreads import arcticSpreadsForInstrumentData, spreadsForInstrumentData
from sysdata.mongodb.mongo_futures_contracts import mongoFuturesContractData

from sysdata.futures.multiple_prices import futuresMultiplePricesData
from sysdata.futures.adjusted_prices import futuresAdjustedPricesData
from sysdata.futures.futures_per_contract_prices import futuresContractPriceData

from sysdata.data_blob import dataBlob

from sysobjects.multiple_prices import price_name
from sysobjects.contract_dates_and_expiries import listOfContractDateStr

from sysproduction.data.generic_production_data import productionDataLayerGeneric


class diagPrices(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list([
            arcticFuturesContractPriceData, arcticFuturesAdjustedPricesData,
         arcticFuturesMultiplePricesData, mongoFuturesContractData,
        arcticSpreadsForInstrumentData]
        )
        return data


    def get_intraday_frequency_for_historical_download(self) -> Frequency:
        config = self.data.config
        intraday_frequency_as_str = config.get_element_or_missing_data("intraday_frequency")
        intraday_frequency = from_config_frequency_to_frequency(intraday_frequency_as_str)

        if intraday_frequency is missing_data:
            error_msg = "Intraday frequency of %s is not recognised as a valid frequency" % str(intraday_frequency)
            self.log.critical(error_msg)
            raise Exception(error_msg)

        return intraday_frequency

    def get_adjusted_prices(self, instrument_code: str) -> futuresAdjustedPrices:
        adjusted_prices =   self.db_futures_adjusted_prices_data.get_adjusted_prices(
            instrument_code)

        return adjusted_prices

    def get_list_of_instruments_in_multiple_prices(self) -> list:
        list_of_instruments = self.db_futures_multiple_prices_data.get_list_of_instruments()

        return list_of_instruments

    def get_multiple_prices(self, instrument_code: str) -> futuresMultiplePrices:
        multiple_prices= self.db_futures_multiple_prices_data.get_multiple_prices(
            instrument_code)

        return multiple_prices

    def get_prices_for_contract_object(self, contract_object: futuresContract) -> futuresContractPrices:
        prices = self.db_futures_contract_price_data.get_prices_for_contract_object(
            contract_object)

        return prices

    def get_current_priced_contract_prices_for_instrument(self, instrument_code: str)  -> futuresContractPrices:
        multiple_prices = self.get_multiple_prices(instrument_code)
        current_priced_contract_prices = multiple_prices[price_name]

        return current_priced_contract_prices

    def get_list_of_instruments_with_contract_prices(self) -> list:
        unique_list_of_instruments =self.db_futures_contract_price_data.get_list_of_instrument_codes_with_price_data()

        return unique_list_of_instruments

    def contract_dates_with_price_data_for_instrument_code(self, instrument_code: str) -> listOfContractDateStr:
        list_of_contract_date_str = self.db_futures_contract_price_data.contract_dates_with_price_data_for_instrument_code(instrument_code)

        return list_of_contract_date_str

    def get_last_matched_date_and_prices_for_contract_list(
            self,
            instrument_code: str,
            list_of_contract_date_str: list,
            contracts_to_match=arg_not_supplied) -> (datetime.datetime, list):
        """
        Get a list of matched prices; i.e. from a date when we had both forward and current prices
        If we don't have all the prices, will do the best it can

        :param instrument_code:
        :param contract_list: contract date_str to get prices for
        :param contracts_to_match: (default: contract_list) contracts to match against each other
        :return: list of prices, in same order as contract_list
        """
        if contracts_to_match is arg_not_supplied:
            contracts_to_match = list_of_contract_date_str

        dict_of_prices = self.get_dict_of_prices_for_contract_list(
            instrument_code, list_of_contract_date_str
        )

        last_matched_date, last_matched_prices = get_last_matched_date_and_prices_for_contract_list(dict_of_prices, contracts_to_match, list_of_contract_date_str)

        return last_matched_date, last_matched_prices

    def get_dict_of_prices_for_contract_list(
            self, instrument_code: str, list_of_contract_date_str: list) -> dictFuturesContractPrices:
        dict_of_prices = {}
        for contract_date_str in list_of_contract_date_str:
            if contract_date_str is missing_contract:
                continue
            # Could blow up here if don't have prices for a contract??
            contract = futuresContract(instrument_code, contract_date_str)
            prices = self.get_prices_for_contract_object(contract)
            dict_of_prices[contract_date_str] = prices

        dict_of_prices = dictFuturesContractPrices(dict_of_prices)

        return dict_of_prices

    def get_spreads(self, instrument_code: str) -> spreadsForInstrument:
        return self.db_spreads_for_instrument_data.get_spreads(instrument_code)

    @property
    def db_futures_adjusted_prices_data(self) -> futuresAdjustedPricesData:
        return self.data.db_futures_adjusted_prices

    @property
    def db_futures_multiple_prices_data(self) -> futuresMultiplePricesData:
        return self.data.db_futures_multiple_prices

    @property
    def db_futures_contract_price_data(self) -> futuresContractPriceData:
        return self.data.db_futures_contract_price

    @property
    def db_spreads_for_instrument_data(self) -> spreadsForInstrumentData:
        return self.data.db_spreads_for_instrument


class updatePrices(productionDataLayerGeneric):
    def _add_required_classes_to_data(self, data) -> dataBlob:
        data.add_class_list([
            arcticFuturesContractPriceData, arcticFuturesMultiplePricesData,
         mongoFuturesContractData, arcticFuturesAdjustedPricesData,
        arcticSpreadsForInstrumentData])

        return data


    def update_prices_for_contract(
        self, contract_object: futuresContract,
            new_prices: futuresContractPrices,
            check_for_spike: bool=True
    ) -> int:

        error_or_rows_added = self.db_futures_contract_price_data.update_prices_for_contract(
            contract_object, new_prices, check_for_spike=check_for_spike
        )
        return error_or_rows_added

    def add_multiple_prices(
        self, instrument_code: str, updated_multiple_prices: futuresMultiplePrices, ignore_duplication=True
    ):
        self.db_futures_multiple_prices_data.add_multiple_prices(
            instrument_code, updated_multiple_prices, ignore_duplication=ignore_duplication
        )

    def add_adjusted_prices(
        self, instrument_code: str, updated_adjusted_prices: futuresAdjustedPrices, ignore_duplication=True
    ):
        self.db_futures_adjusted_prices_data.add_adjusted_prices(
            instrument_code, updated_adjusted_prices, ignore_duplication=ignore_duplication
        )

    def add_spread_entry(self, instrument_code: str, spread: float):
        self.db_spreads_for_instrument_data.add_spread_entry(instrument_code,
                                                             spread=spread)

    @property
    def db_futures_adjusted_prices_data(self) -> futuresAdjustedPricesData:
        return self.data.db_futures_adjusted_prices

    @property
    def db_futures_multiple_prices_data(self) -> futuresMultiplePricesData:
        return self.data.db_futures_multiple_prices

    @property
    def db_futures_contract_price_data(self) -> futuresContractPriceData:
        return self.data.db_futures_contract_price

    @property
    def db_spreads_for_instrument_data(self) -> spreadsForInstrumentData:
        return self.data.db_spreads_for_instrument


def get_valid_instrument_code_from_user(
        data: dataBlob=arg_not_supplied,
        allow_all: bool=False,
        all_code = "ALL",
            source = 'multiple') -> str:
    if data is arg_not_supplied:
        data = dataBlob()
    instrument_code_list = get_list_of_instruments(data, source=source)
    invalid_input = True
    input_prompt = "Instrument code?"
    if allow_all:
        input_prompt = input_prompt + "(Return for ALL)"
    while invalid_input:
        instrument_code = input(input_prompt)

        if allow_all:
            if instrument_code == "" or instrument_code == "ALL":
                return all_code

        if instrument_code in instrument_code_list:
            break

        print("%s is not in list %s derived from source: %s" % (instrument_code, instrument_code_list, source))

    return instrument_code

def get_list_of_instruments(data: dataBlob=arg_not_supplied, source = 'multiple') -> list:
    price_data = diagPrices(data)
    if source=="multiple":
        return price_data.get_list_of_instruments_in_multiple_prices()
    elif source=="single":
        return price_data.get_list_of_instruments_with_contract_prices()
    else:
        raise Exception("%s not recognised must be multiple or single" % source)
