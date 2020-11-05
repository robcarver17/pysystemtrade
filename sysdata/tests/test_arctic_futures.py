import unittest
from sysdata.arctic.arctic_futures_per_contract_prices import (
    arcticFuturesContractPriceData,
)
from sysobjects.contracts import futuresContract
import pandas as pd


class MyTestCase(unittest.TestCase):
    def test_futures_prices(self):
        data = arcticFuturesContractPriceData(database_name="test")
        data._arctic.store.delete_library(data._arctic.library_name)

        # we need some sham data
        dummy_series = [5.0] * 5
        dummy_series2 = [2.0] * 5

        price_data = pd.DataFrame(
            dict(
                OPEN=dummy_series,
                CLOSE=dummy_series,
                HIGH=dummy_series,
                LOW=dummy_series,
                SETTLE=dummy_series,
            ),
            index=pd.date_range(
                pd.datetime(
                    2000,
                    1,
                    1),
                pd.datetime(
                    2000,
                    1,
                    5)),
        )

        price_data2 = pd.DataFrame(
            dict(
                OPEN=dummy_series2,
                CLOSE=dummy_series2,
                HIGH=dummy_series2,
                LOW=dummy_series2,
                SETTLE=dummy_series2,
            ),
            index=pd.date_range(
                pd.datetime(
                    2000,
                    1,
                    1),
                pd.datetime(
                    2000,
                    1,
                    5)),
        )

        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing one"
        )
        self.assertEqual(list_of_contracts, [])

        empty_thing = data.get_prices_for_instrument_code_and_contract_date(
            "thing one", "201801"
        )
        self.assertEqual(len(empty_thing.index), 0)
        self.assertEqual(
            data.has_data_for_instrument_code_and_contract_date(
                "thing one", "201801"), False, )

        data.write_prices_for_contract_object(
            futuresContract.simple("thing one", "201801"), price_data
        )
        data.write_prices_for_contract_object(
            futuresContract.simple("thing one", "20180215"), price_data
        )
        data.write_prices_for_contract_object(
            futuresContract.simple("thing two", "201803"), price_data2
        )

        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing one"
        )
        self.assertEqual(list_of_contracts, ["20180100", "20180215"])
        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing two"
        )
        self.assertEqual(list_of_contracts, ["20180300"])

        self.assertEqual(
            data.has_data_for_instrument_code_and_contract_date(
                "thing one", "201801"), True, )
        self.assertEqual(
            data.has_data_for_instrument_code_and_contract_date(
                "thing one", "20180215"
            ),
            True,
        )
        self.assertEqual(
            data.has_data_for_instrument_code_and_contract_date(
                "thing one", "201807"), False, )
        self.assertEqual(
            data.has_data_for_contract(
                futuresContract.simple(
                    "thing two", "201803")), True, )

        getback1 = data.get_prices_for_instrument_code_and_contract_date(
            "thing one", "201801"
        )
        getback2 = data.get_prices_for_contract_object(
            futuresContract.simple("thing two", "201803")
        )

        self.assertEqual(getback1.OPEN.values[0], 5.0)
        self.assertEqual(getback2.OPEN.values[0], 2.0)

        data.delete_prices_for_contract_object(
            futuresContract.simple("thing one", "201807"), areyousure=True
        )

        data.delete_prices_for_contract_object(
            futuresContract.simple("thing one", "201801"), areyousure=True
        )
        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing one"
        )
        self.assertEqual(list_of_contracts, ["20180215"])
        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing two"
        )
        self.assertEqual(list_of_contracts, ["20180300"])

        data.delete_prices_for_contract_object(
            futuresContract.simple("thing one", "20180215"), areyousure=True
        )
        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing one"
        )
        self.assertEqual(list_of_contracts, [])

        data.delete_prices_for_contract_object(
            futuresContract.simple("thing two", "201803"), areyousure=True
        )
        list_of_contracts = data.contracts_with_price_data_for_instrument_code(
            "thing two"
        )
        self.assertEqual(list_of_contracts, [])


if __name__ == "__main__":
    unittest.main()
