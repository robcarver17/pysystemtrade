import pandas as pd
from sysdata.data import baseData
from sysdata.futures.contracts import futuresContract
from syscore.pdutils import full_merge_of_existing_data, merge_newer_data

PRICE_DATA_COLUMNS = ['OPEN', 'HIGH', 'LOW', 'FINAL']
PRICE_DATA_COLUMNS.sort() # needed for pattern matching
FINAL_COLUMN = 'FINAL'

class futuresContractPrices(pd.DataFrame):
    """
    simData frame in specific format containing per contract information
    """

    def __init__(self, data):
        """

        :param data: pd.DataFrame or something that could be passed to it
        """

        data_present = list(data.columns)
        data_present.sort()

        try:
            assert data_present == PRICE_DATA_COLUMNS
        except AssertionError:
            raise Exception("futuresContractPrices has to conform to pattern")

        super().__init__(data)

        self._is_empty=False


    @classmethod
    def create_empty(futuresContractPrices):
        """
        Our graceful fail is to return an empty, but valid, dataframe
        """

        data = pd.DataFrame(columns=PRICE_DATA_COLUMNS)

        futures_contract_prices = futuresContractPrices(data)

        futures_contract_prices._is_empty = True
        return futures_contract_prices

    @classmethod
    def only_have_final_prices(futuresContractPrices, data):
        data = pd.DataFrame(data, columns=[FINAL_COLUMN])
        data = data.reindex(columns = PRICE_DATA_COLUMNS)

        futures_contract_prices = futuresContractPrices(data)

        return futures_contract_prices

    def return_final_prices(self):
        data = self[FINAL_COLUMN]

        return futuresContractFinalPrices(data)


    def empty(self):
        return

    def merge_with_other_prices(self, new_futures_per_contract_prices, only_add_rows=True):
        """
        Merges self with new data.
        If only_add_rows is True,
        Otherwise: Any Nan in the existing data will be replaced (be careful!)

        :param new_futures_per_contract_prices: another futures per contract prices object

        :return: merged futures_per_contract object
        """
        if only_add_rows:
            return self.add_rows_to_existing_data(new_futures_per_contract_prices)
        else:
            return self._full_merge_of_existing_data(new_futures_per_contract_prices)

    def _full_merge_of_existing_data(self, new_futures_per_contract_prices):
        """
        Merges self with new data.
        Any Nan in the existing data will be replaced (be careful!)

        :param new_futures_per_contract_prices: the new data
        :return: updated data, doesn't update self
        """

        merged_data = full_merge_of_existing_data(self, new_futures_per_contract_prices)

        return futuresContractPrices(merged_data)

    def add_rows_to_existing_data(self, new_futures_per_contract_prices):
        """
        Merges self with new data.
        Only newer data will be added

        :param new_futures_per_contract_prices: another futures per contract prices object

        :return: merged futures_per_contract object
        """

        merged_futures_prices = merge_newer_data(self, new_futures_per_contract_prices)
        merged_futures_prices = futuresContractPrices(merged_futures_prices)

        return merged_futures_prices


class futuresContractFinalPrices(pd.Series):
    """
    Just the final prices from a futures contract
    """
    def __init__(self, data):
        super().__init__(data)


class dictFuturesContractPrices(dict):
    """
    A dict of futures contract prices

    Keys are contract_objects

    We can use standard dict methods, but convenience methods are included
    """

    def __repr__(self):
        object_repr = "Dict of futures contract prices with %d contracts" % len(self.keys())
        return object_repr

    def final_prices(self):
        """

        :return: dict of final prices
        """

        all_contract_ids = list(self.keys())
        final_price_dict_as_list = []
        for contract_id in all_contract_ids:
            final_prices = self[contract_id].return_final_prices()
            # for this to work return_final_prices must be a pd.Series type object
            final_prices.name = contract_id
            final_price_dict_as_list.append((contract_id, final_prices))

        final_prices_dict = dictFuturesContractFinalPrices(final_price_dict_as_list)

        return final_prices_dict


    def sorted_contract_ids(self):
        """
        Time sorted contract ids
        :return:
        """

        all_contract_ids = list(self.keys())
        all_contract_ids.sort()

        return all_contract_ids

    def earliest_contract_id(self):
        """
        First contract id
        :return: str
        """

        return self.sorted_contract_ids()[0]

    def earliest_date_in_earliest_contract_id(self):
        """
        Oldest data in earliest contract (may not be the same as oldest data universally)

        :return: datetime
        """

        earliest_contract_id = self.earliest_contract_id()
        earliest_contract_data = self[earliest_contract_id]
        earliest_date_in_data = earliest_contract_data.index[0].to_pydatetime()

        return earliest_date_in_data

class dictFuturesContractFinalPrices(dict):
    def __repr__(self):
        object_repr = "Dict of final futures contract prices with %d contracts" % len(self.keys())
        return object_repr

    def sorted_contract_ids(self):
        """
        Time sorted contract ids
        :return:
        """

        all_contract_ids = list(self.keys())
        all_contract_ids.sort()

        return all_contract_ids

    def last_contract_id(self):
        sorted_contract_ids = self.sorted_contract_ids()

        return sorted_contract_ids[-1]

BASE_CLASS_ERROR = "You have used a base class for futures price data; you need to use a class that inherits with a specific data source"

class futuresContractPriceData(baseData):
    """
    Extends the baseData object to a data source that reads in and writes prices for specific futures contracts

    This would normally be extended further for information from a specific source eg quandl, arctic

    Access via: object.get_prices_for_instrumentCode_and_contractDate('EDOLLAR','201702']
     or object.get_prices_for_contract_object(futuresContract(....))
    """

    def __repr__(self):
        return "Individual futures contract price data - DO NOT USE"


    def __getitem__(self, contract_object):
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

    def get_contracts_with_price_data(self):
        """

        :return: list of futuresContact
        """
        raise NotImplementedError(BASE_CLASS_ERROR)

    def get_instruments_with_price_data(self):
        """

        :return: list of str
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        list_of_instruments = [contract.instrument_code for contract in list_of_contracts_with_price_data]

        # will contain duplicates, make unique
        list_of_instruments = list(set(list_of_instruments))

        return list_of_instruments



    def has_data_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date( instrument_code, contract_date, "has_data_for_contract")

        return ans


    def has_data_for_contract(self, contract_object):

        contract_date = contract_object.date
        instrument_code = contract_object.instrument_code

        if contract_date in self.contract_dates_with_price_data_for_instrument_code(instrument_code):
            return True
        else:
            return False

    def get_all_prices_for_instrument(self, instrument_code):
        """
        Get all the prices for this code, returned as dict

        :param instrument_code: str
        :return: dictFuturesContractPrices
        """

        contractid_list = self.contract_dates_with_price_data_for_instrument_code(instrument_code)
        dict_of_prices = dictFuturesContractPrices([(contract_date,
                         self.get_prices_for_instrument_code_and_contract_date(instrument_code, contract_date))

                         for contract_date in contractid_list])

        return dict_of_prices


    def get_prices_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date( instrument_code, contract_date, "get_prices_for_contract_object")

        return ans


    def get_prices_for_contract_object(self, contract_object):
        """
        get some prices

        :param contract_object:  futuresContract
        :return: data
        """

        if self.has_data_for_contract(contract_object):
            return self._get_prices_for_contract_object_no_checking(contract_object)
        else:
            return futuresContractPrices.create_empty()

    def get_prices_at_frequency_for_instrument_code_and_contract_date(self, instrument_code, contract_date, freq="D"):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :param freq: str; one of D, H, M5, M, 10S, S
        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date(instrument_code, contract_date,
                                                                                  "get_prices_at_frequency_for_contract_object", freq=freq)

        return ans

    def get_prices_at_frequency_for_contract_object(self, contract_object, freq="D"):
        """
        get some prices

        :param contract_object:  futuresContract
        :param freq: str; one of D, H, 5M, M, 10S, S
        :return: data
        """

        if self.has_data_for_contract(contract_object):
            return self._get_prices_at_frequency_for_contract_object_no_checking(contract_object, freq=freq)
        else:
            return futuresContractPrices.create_empty()


    def _get_prices_at_frequency_for_contract_object_no_checking(self, contract_object, freq):
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

    def write_prices_for_instrument_code_and_contract_date(self, instrument_code, contract_date, futures_price_data,
                                                           ignore_duplication=False):
        """
        Write some prices

        :param futures_price_data:
        :param ignore_duplication: bool, to stop us overwriting existing prices
        :return: None
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date( instrument_code, contract_date, "write_prices_for_contract_object",
                                                                                   ignore_duplication=ignore_duplication)

        return ans


    def write_prices_for_contract_object(self, futures_contract_object, futures_price_data, ignore_duplication=False):
        """
        Write some prices

        :param futures_contract_object:
        :param futures_price_data:
        :param ignore_duplication: bool, to stop us overwriting existing prices
        :return: None
        """

        new_log = self.log.setup(instrument_code=futures_contract_object.instrument_code,
                                 contract_date=futures_contract_object.date)
        if self.has_data_for_contract(futures_contract_object):
            if ignore_duplication:
                pass
            else:
                new_log.warn("There is already existing data, you have to delete it first")
                return None

        self._write_prices_for_contract_object_no_checking(futures_contract_object, futures_price_data)


    def _write_prices_for_contract_object_no_checking(self, futures_contract_object, futures_price_data):
        """
        Write some prices

        We don't check to see if we've already written some, so only call directly with care
        :param futures_contract_object:
        :param futures_price_data:
        :return: None
        """

        raise NotImplementedError(BASE_CLASS_ERROR)

    def get_actual_expiry_date_for_instrument_code_and_contract_date(self, instrument_code, contract_date):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :return: data
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date( instrument_code, contract_date, "get_actual_expiry_date_for_contract")

        return ans

    def get_actual_expiry_date_for_contract(self, futures_contract_object):
        raise NotImplementedError(BASE_CLASS_ERROR)

    def update_prices_for_for_instrument_code_and_contract_date(self, instrument_code, contract_date,
                                                                new_futures_per_contract_prices):
        """
        Convenience method for when we have a code and date str, and don't want to build an object

        :new futures prices: futuresPrices object
        :return: int, number of rows added
        """

        ans = self._perform_contract_method_for_instrument_code_and_contract_date( instrument_code, contract_date,
                                                            "update_prices_for_contract",
                                                            new_futures_per_contract_prices = new_futures_per_contract_prices)

        return ans

    def update_prices_for_contract(self, futures_contract_object, new_futures_per_contract_prices):
        """
        Reads existing data, merges with new_futures_prices, writes merged data

        :param new_futures_prices:
        :return: int, number of rows
        """
        new_log = self.log.setup(instrument_code=futures_contract_object.instrument_code,
                                 contract_date=futures_contract_object.date)

        old_prices = self.get_prices_for_contract_object(futures_contract_object)
        merged_prices = old_prices.add_rows_to_existing_data(new_futures_per_contract_prices)

        rows_added = len(merged_prices) - len(old_prices)

        if rows_added==0:
            new_log.msg("No additional data since %s " % str(old_prices.index[-1]))
            return 0

        # We have guaranteed no duplication
        self.write_prices_for_contract_object(futures_contract_object, merged_prices, ignore_duplication=True)

        new_log.msg("Added %d additional rows of data")

        return rows_added

    def delete_prices_for_contract_object(self, futures_contract_object, areyousure=False):
        """

        :param futures_contract_object:
        :return:
        """

        if not areyousure:
            raise Exception("You have to be sure to delete prices_for_contract_object!")

        if self.has_data_for_contract(futures_contract_object):
            self._delete_prices_for_contract_object_with_no_checks_be_careful(futures_contract_object)
        else:
            self.log.warn("Tried to delete non existent contract")

    def delete_all_prices_for_instrument_code(self, instrument_code, areyousure=False):
        ## We don't pass areyousure, otherwise if we weren't sure would get multiple exceptions
        if not areyousure:
            raise Exception("You have to be sure to delete_all_prices_for_instrument!")

        all_contracts_to_delete = self.contracts_with_price_data_for_instrument_code(instrument_code)
        for contract in all_contracts_to_delete:
            self.delete_prices_for_contract_object(contract, areyousure=True)

    def _delete_prices_for_contract_object_with_no_checks_be_careful(self, futures_contract_object):
        raise NotImplementedError(BASE_CLASS_ERROR)


    def contracts_with_price_data_for_instrument_code(self, instrument_code):
        """
        Valid contracts

        :param instrument_code: str
        :return: list of contract_date
        """

        list_of_contracts_with_price_data = self.get_contracts_with_price_data()
        list_of_contracts = [contract for contract in list_of_contracts_with_price_data if contract.instrument_code==instrument_code]

        return list_of_contracts

    def contract_dates_with_price_data_for_instrument_code(self, instrument_code):
        """

        :param instrument_code:
        :return: list of str
        """

        list_of_contracts_with_price_data = self.contracts_with_price_data_for_instrument_code(instrument_code)
        contract_dates = [str(contract.contract_date) for contract in list_of_contracts_with_price_data if contract.instrument_code == instrument_code]

        return contract_dates

    def _perform_contract_method_for_instrument_code_and_contract_date(self, instrument_code, contract_date, method_name, **kwargs):
        contract_object = self._object_given_instrumentCode_and_contractDate(instrument_code, contract_date)
        method = getattr(self, method_name)

        return method(contract_object, **kwargs)

    def _object_given_instrumentCode_and_contractDate(self, instrument_code, contract_date):
        """
        Quickly go from eg "EDOLLAR" "201801" to an object

        :param instrument_code: str
        :param contract_date: str
        :return: futuresContract
        """

        contract_object = futuresContract(instrument_code, contract_date)

        return contract_object
