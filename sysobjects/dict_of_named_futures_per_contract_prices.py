import pandas as pd

from syscore.pdutils import merge_data_series_with_label_column

## CHECK IF ALL THESE ARE NEEDED...

price_name = "PRICE"
carry_name = "CARRY"
forward_name = "FORWARD"
price_column_names = dict(PRICE=price_name, CARRY=carry_name, FORWARD=forward_name)
list_of_price_column_names = list(price_column_names.values())
list_of_price_column_names.sort()
contract_suffix = "_CONTRACT"


def contract_name_from_column_name(column_name):
    return column_name + contract_suffix


contract_column_names = dict(
    [
        (key, contract_name_from_column_name(key))
        for key in list_of_price_column_names
    ]
)
list_of_contract_column_names = list(contract_column_names.values())


class dictNamedFuturesContractFinalPrices(dict):
    ## keys are PRICE, CARRY, FORWARD
    def __init__(self, entry_dict):
        _check_key_list_is_valid_against_names(entry_dict)
        super().__init__(entry_dict)

    def __repr__(self):
        return "dictNamedFuturesContractFinalPrices with keys %s" % str(self.keys())


def _check_key_list_is_valid_against_names(some_dict):
    keys = list(some_dict.keys())
    keys.sort()
    try:
        assert keys == list_of_price_column_names
    except:
        raise Exception("Object %s should have keys %s!" % (str(some_dict), str(list_of_price_column_names)))


class futuresNamedContractFinalPricesWithContractID(pd.DataFrame):
    """
    Just the final prices from a futures contract, plus
    Columns are named 'NAME' and 'NAME_CONTRACT'
    """

    def __init__(
            self,
            ts_of_prices: pd.Series,
            ts_of_contracts: pd.Series,
            price_column_name:str = list_of_price_column_names[0]
            ):
        """

        :param price_and_contract_data: pd.DataFrame with two columns
        :param column_name: column name for price
        """
        assert price_column_name in list_of_price_column_names

        price_and_contract_data = pd.concat([ts_of_prices, ts_of_contracts], axis=1)

        contract_column_name = price_column_name + contract_suffix
        price_and_contract_data.columns = [price_column_name, contract_column_name]

        super().__init__(price_and_contract_data)

        self._price_column_name = price_column_name
        self._contract_column_name = contract_column_name

    @property
    def price_column_name(self) ->str:
        return self._price_column_name

    @property
    def contract_column_name(self) ->str:
        return self._contract_column_name

    @property
    def prices(self) ->pd.Series:
        return self[self.price_column_name]

    @property
    def ts_of_contract_str(self) ->pd.Series:
        return self[self.contract_column_name]

    def as_pd(self):
        return pd.DataFrame(self)

    @classmethod
    def create_with_single_contractid(
        futuresNamedContractFinalPricesWithContractID,
        ts_of_prices: pd.Series,
        contractid: str,
        price_column_name=price_name
    ):
        """

        :param price_data: futuresContractFinalPrices
        :param contractid: str YYYYMMDD
        :param column_name: column name for price
        :param contract_column_name_suffix: column name for contract
        """

        contract_data = [contractid] * len(ts_of_prices)
        ts_of_contracts = pd.Series(contract_data, index = ts_of_prices.index)

        return futuresNamedContractFinalPricesWithContractID(
            ts_of_prices, ts_of_contracts, price_column_name=price_column_name)

    def prices_after_date(self, date_slice):
        prices = self.prices[date_slice:]
        contracts = self.ts_of_contract_str[date_slice:]
        return futuresNamedContractFinalPricesWithContractID(prices, contracts, price_column_name=self.price_column_name)

    def final_contract(self) ->str:
        """

        :return: last value in contract id column
        """
        contract_ids = self.ts_of_contract_str

        return contract_ids[-1]

    def check_all_contracts_equal_to(self, test_contractid: str) ->bool:
        """
        Check to see if all contracts are the same as contractid

        :param contractid: str yyyymmdd
        :return: bool
        """

        contract_ids = self.ts_of_contract_str

        check_equality = [
            str(int(cid)) == test_contractid for cid in contract_ids.values]

        return all(check_equality)

    def merge_data(self, new_data):
        """
        Assuming that contracts all match,

        merge the data series together

        :param new_data: object of same type
        :return: object of same type
        """
        merged_data = _merge_futures_contract_final_prices_with_contract_id(self, new_data)

        return merged_data


def _merge_futures_contract_final_prices_with_contract_id(original_data: futuresNamedContractFinalPricesWithContractID,
                                                          new_data: futuresNamedContractFinalPricesWithContractID)\
                                                        -> futuresNamedContractFinalPricesWithContractID:

    if len(new_data) == 0:
        return original_data

    _assert_merge_is_valid(original_data, new_data)

    price_column_name = original_data.price_column_name
    contract_column_name = original_data.contract_column_name

    col_names_for_merger = dict(
        data= price_column_name,
        label= contract_column_name)

    merged_data_as_pd = merge_data_series_with_label_column(
        original_data, new_data, col_names=col_names_for_merger
    )

    merged_data = futuresNamedContractFinalPricesWithContractID(merged_data_as_pd[price_column_name],
                                                                merged_data_as_pd[contract_column_name],
                                                                price_column_name=original_data.price_column_name)

    return merged_data


def _assert_merge_is_valid(original_data: futuresNamedContractFinalPricesWithContractID,
                           new_data: futuresNamedContractFinalPricesWithContractID):

    last_contract_in_original_data = original_data.final_contract()

    try:
        assert new_data.check_all_contracts_equal_to(
            last_contract_in_original_data)
    except BaseException:
        raise Exception(
            "When merging data, final contractid in original data must match all new data"
        )
    try:
        assert new_data.price_column_name == original_data.price_column_name
        assert new_data.contract_column_name == original_data.contract_column_name
    except BaseException:
        raise Exception("When merging data, column names must match")


class setOfNamedContracts(dict):
    def __init__(self, entry_dict):
        super().__init__(entry_dict)
        _check_key_list_is_valid_against_names(entry_dict)

    def __repr__(self):
        return "setOfContracts %s" % str([(key,value) for key,value in self.items()])

    @property
    def price(self):
        return self[price_name]

    @property
    def carry(self):
        return self[carry_name]

    @property
    def forward(self):
        return self[forward_name]

    def furthest_out_contract_date(self) ->str:
        current_contract_list = list(self.values())
        furthest_out_contract_date = max(current_contract_list)

        return furthest_out_contract_date

class dictFuturesNamedContractFinalPricesWithContractID(dict):
    # options for construction:
    # - pulled out of multiple prices
    # - from two dicts of prices, and contract ids
    def __init__(self, dict_with_cids: dict):
        """

        :param dict_with_cids: dict, containing futuresNamedContractFinalPricesWithContractID
        :return: object
        """
        super().__init__(dict_with_cids)
        _check_key_list_is_valid_against_names(dict_with_cids)

    def __repr__(self):
        return "dictFuturesNamedContractFinalPricesWithContractID with keys %s" % str(self.keys())

    @classmethod
    def create_from_two_dicts(
        dictFuturesNamedContractFinalPricesWithContractID,
        dict_of_final_prices: dictNamedFuturesContractFinalPrices,
        dict_of_contract_ids: setOfNamedContracts,
    ):
        """

        :param dict_of_final_prices: dict of futuresContractFinalPrices
        :param dict_of_contract_ids: dict of str, yyyymmdd contract_ids. Keys must match
        """

        new_dict = {}
        for key in list_of_price_column_names:
            try:
                price_series = dict_of_final_prices[key]
                contract_id = dict_of_contract_ids[key]
            except KeyError:
                raise Exception(
                    "key value %s missing from dict_of_contract_ids or price series" %
                    key)

            prices_with_contractid = (
                futuresNamedContractFinalPricesWithContractID.create_with_single_contractid(
                    price_series, contract_id, price_column_name=key))
            new_dict[key] = prices_with_contractid

        return dictFuturesNamedContractFinalPricesWithContractID(new_dict)

    def merge_data(self, new_price_dict):
        """
        Update this data with some new data, element by element

        :param new_price_dict: another of the same class. Keys and column names must match. Contract IDs must match
        :return:  merged price dict
        """
        merged_data = _merge_dictFuturesContractFinalPricesWithContractID(self, new_price_dict)

        return merged_data


def _merge_dictFuturesContractFinalPricesWithContractID(first_dict: dictFuturesNamedContractFinalPricesWithContractID,
                                                        second_dict: dictFuturesNamedContractFinalPricesWithContractID)\
                                                        -> dictFuturesNamedContractFinalPricesWithContractID:
    # for each element, run a merge
    list_of_keys = list_of_price_column_names
    merged_dict = {}
    for key_name in list_of_keys:
        current_data = first_dict[key_name]
        try:
            new_data = second_dict[key_name]
        except KeyError:
            raise Exception(
                "Key name mismatch when merging price data, %s missing from new data" %
                key_name)
        try:
            merged_data = current_data.merge_data(new_data)
        except Exception as e:
            raise e

        merged_dict[key_name] = merged_data

    merged_dict = dictFuturesNamedContractFinalPricesWithContractID(merged_dict)

    return merged_dict