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

        merged_futures_prices = merge_newer_data(pd.DataFrame(self), new_futures_per_contract_prices)
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

class futuresContractFinalPricesWithContractID(pd.DataFrame):
    """
    Just the final prices from a futures contract, plus
    Columns are named 'NAME' and 'NAME_CONTRACT'
    """
    def __init__(self, price_data, contractid, column_name = 'PRICE', contract_suffix="_CONTRACT"):
        """

        :param price_data: futuresContractFinalPrices
        :param contractid: str YYYYMMDD
        :param column_name: column name for price
        :param contract_suffix: column name for contract
        """

        contract_data = [contractid]*len(price_data)
        data = pd.DataFrame(dict(px=list(price_data.values), contracts=contract_data),
                            index = price_data.index)

        contract_name = column_name+contract_suffix
        data.columns=[column_name, contract_name]
        super().__init__(data)

        self._price_column = column_name
        self._contract_column = contract_name

    def merge_with_new_data(self, new_data):
        """

        :param new_data: same object type, columns must match, first contractid in new data must match last in old data
        :return: new object
        """

        pass

    def contract_ids(self):
        contract_column = self._contract_column
        contract_ids = self[contract_column]

        return contract_ids

    def final_contract(self):
        """

        :return: last value in contract id column
        """
        contract_ids = self.contract_ids()

        return contract_ids[-1]

    def check_all_contracts_equal_to(self, test_contractid):
        """
        Check to see if all contracts are the same as contractid

        :param contractid: str yyyymmdd
        :return: bool
        """

        contract_ids = self.contract_ids()

        check_equality = [cid == test_contractid for cid in contract_ids.values]

        return all(check_equality)

    def merge(self, new_price_data):
        """
        Assuming that contracts all match,

        merge the data series together

        WHAT IF WE HAVE MIXED DATA....?

        :param new_price_data: object of same type
        :return: object of same type
        """
        original_data = self
        new_format = "new_%s"
        new_price_data.columns = [new_format % colname for colname in new_price_data.columns]

        contract_column = self._contract_column
        price_column = self._price_column

        new_contract_column = new_format % contract_column
        new_price_column = new_format % price_column

        joint_data_contractids = pd.concat([original_data[contract_column],
                                            new_price_data[new_contract_column]], axis=1)


        new_data_start = new_price_data.index[0]

        joint_data_contractids = joint_data_contractids.sort_index()

        existing_contract_ids_in_new_period = joint_data_contractids[contract_column][new_data_start:].ffill()
        new_contract_ids_in_new_period = joint_data_contractids[new_contract_column][new_data_start:].ffill()

        # Only interested in data once the existing and new are matching
        # Before this, was probably a roll
        # Data is same length, and timestamp matched, so equality of values is sufficient
        period_equal = [x==y for x,y in zip(new_contract_ids_in_new_period.values,
                                             existing_contract_ids_in_new_period.values)]

        # Want last False value
        period_equal.reverse()
        first_false_in_reversed_list = period_equal.index(False)

        last_true_before_first_false_in_reversed_list = first_false_in_reversed_list-1

        reversed_time_index = new_contract_ids_in_new_period.index[::-1]
        last_true_before_first_false_in_reversed_list_date = reversed_time_index[last_true_before_first_false_in_reversed_list]
        first_false_in_reversed_list_date = reversed_time_index[first_false_in_reversed_list]

        first_true_after_last_false_date = last_true_before_first_false_in_reversed_list_date
        last_false_date = first_false_in_reversed_list_date

        # From the date after this, can happily merge new and old data

        # Concat the two price series together, fill to the left
        # This will replace any NA values in existing prices with new ones

        joint_price_data_to_merge = pd.concat([original_data[price_column],
                                               new_price_data[new_price_column]], axis=1)
        joint_price_data_to_merge_to_use = joint_price_data_to_merge[first_true_after_last_false_date:]

        joint_price_data_filled_across = joint_price_data_to_merge_to_use.bfill(1)
        merged_price_data = joint_price_data_filled_across[price_column]
        merged_contract_id =

        # for older data, keep older data
        original_data_to_use = original_data[:last_false_date]


class dictFuturesContractFinalPricesWithContractID(dict):
    ## options for construction:
    ##    - pulled out of multiple prices
    ##    - from two dicts of prices, and contract ids
    def __init__(self, dict_with_cids):
        """

        :param dict_with_cids: dict, containing futuresContractFinalPricesWithContractID
        :return: object
        """
        super().__init__(dict_with_cids)

    @classmethod
    def create_from_two_dicts(dictFuturesContractFinalPricesWithContractID,
                              dict_of_final_prices, dict_of_contract_ids):
        """

        :param dict_of_final_prices: dict of futuresContractFinalPrices
        :param dict_of_contract_ids: dict of str, yyyymmdd contract_ids. Keys must match
        """

        new_dict = {}
        for key, price_series in dict_of_final_prices.items():
            try:
                contract_id = dict_of_contract_ids[key]
            except KeyError:
                raise Exception("key value %s missing from dict_of_contract_ids" % key)

            prices_with_contractid = futuresContractFinalPricesWithContractID(price_series, contract_id,
                                                                              column_name = key)
            new_dict[key] = prices_with_contractid

        return dictFuturesContractFinalPricesWithContractID(new_dict)

    def merge_data(self, new_price_dict):
        """
        Update this data with some new data, element by element

        :param new_price_dict: another of the same class. Keys and column names must match. Contract IDs must match
        :return:  merged price dict
        """

        ## for each element, run a merge
        list_of_keys = self.keys()
        merged_dict = {}
        for key_name in list_of_keys:
            current_data = self[key_name]
            try:
                new_data = new_price_dict[key_name]
            except KeyError:
                raise Exception("Key name mismatch when merging price data, %s missing from new data" % key_name)

            merged_data = current_data.merge(new_data)

            merged_dict[key_name] = merged_data

        return merged_dict


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

        new_log.msg("Added %d additional rows of data" % rows_added)

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
