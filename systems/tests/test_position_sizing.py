import copy
import unittest

from systems.account import Account
from systems.tests.testdata import get_test_object_futures_with_comb_forecasts
from systems.basesystem import System
from systems.positionsizing import PositionSizing


class Test(unittest.TestCase):
    def setUp(self):

        (comb, fcs, rules, rawdata, data,
         config) = get_test_object_futures_with_comb_forecasts()
        system = System([rawdata, rules, fcs, comb, PositionSizing()], data,
                        config)

        self.system = system
        self.config = config
        self.rules = rules
        self.rawdata = rawdata
        self.fcs = fcs
        self.forecast_combine = comb
        self.data = data
        self.position_sizing = PositionSizing

    def test_get_combined_forecast(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_combined_forecast("EDOLLAR").values[
                -1], 2.462610227)

    def test_get_price_volatility(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_price_volatility("EDOLLAR").values[
                -1], 0.059789159138)

        ## now without rawdata, should default to calculate on adj price
        system2 = System([
            self.rules, self.fcs, self.forecast_combine,
            self.position_sizing()
        ], self.data, self.config)
        self.assertAlmostEqual(
            system2.positionSize.get_price_volatility("EDOLLAR").values[-1],
            0.059723565)

    def test_get_instrument_sizing_data(self):
        ans = self.system.positionSize.get_instrument_sizing_data("EDOLLAR")
        self.assertEqual(ans[0].values[-1], 97.9875)
        self.assertEqual(ans[1], 2500)

    def test_get_daily_cash_vol_target(self):
        ans_dict = self.system.positionSize.get_daily_cash_vol_target()
        self.assertEqual(ans_dict['base_currency'], "GBP")
        self.assertEqual(ans_dict['annual_cash_vol_target'], 16000.0)
        self.assertEqual(ans_dict['daily_cash_vol_target'], 1000.0)
        self.assertEqual(ans_dict['notional_trading_capital'], 100000.0)
        self.assertEqual(ans_dict['percentage_vol_target'], 16.0)

        # test for missing config defaults
        system2 = System([
            self.rawdata, self.rules, self.fcs, self.forecast_combine,
            self.position_sizing()
        ], self.data)
        ans_dict2 = system2.positionSize.get_daily_cash_vol_target()
        self.assertEqual(ans_dict2['base_currency'], "USD")
        self.assertEqual(ans_dict2['annual_cash_vol_target'], 160000.0)
        self.assertEqual(ans_dict2['daily_cash_vol_target'], 10000.0)
        self.assertEqual(ans_dict2['notional_trading_capital'], 1000000.0)
        self.assertEqual(ans_dict2['percentage_vol_target'], 16.0)

    def test_get_fx_rate(self):
        self.assertEqual(
            self.system.positionSize.get_fx_rate("EDOLLAR").values[-1],
            0.6607594769427981)
        self.assertAlmostEqual(
            self.system.positionSize.get_fx_rate("BUND").values[-1],
            0.72446329811485333)

    def test_get_block_value(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_block_value("EDOLLAR").values[-1],
            2449.6875)

    def test_get_instrument_currency_vol(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_instrument_currency_vol("EDOLLAR")
            .values[-1], 146.46475577626)

    def test_get_instrument_value_vol(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_instrument_value_vol("EDOLLAR")
            .ffill().values[-1], 96.777975417280)

    def test_get_get_volatility_scalar(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_volatility_scalar("EDOLLAR").ffill()
            .values[-1], 10.33292952955)

    def test_get_subsystem_position(self):
        self.assertAlmostEqual(
            self.system.positionSize.get_subsystem_position("EDOLLAR").values[
                -1], 2.5445977941854627)


if __name__ == "__main__":
    unittest.main()
