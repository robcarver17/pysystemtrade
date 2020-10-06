import unittest
from sysdata.quandl.quandl_futures import quandlFuturesContractPriceData


class MyTestCase(unittest.TestCase):
    def test_rollcycle(self):
        data = quandlFuturesContractPriceData()
        ans = data.get_prices_for_instrument_code_and_contract_date(
            "EDOLLAR", "200203")

        self.assertAlmostEqual(
            ans[ans.index == ans.index[0]].SETTLE[0], 92.62, places=2
        )


if __name__ == "__main__":
    unittest.main()
