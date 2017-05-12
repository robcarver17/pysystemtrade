import copy
import unittest

from systems.tests.testdata import get_test_object_futures_with_pos_sizing
from systems.basesystem import System
from systems.portfolio import Portfolios
from systems.account import Account


class Test(unittest.TestCase):
    def setUp(self):

        (posobject, combobject, capobject, rules, rawdata, data,
         config) = get_test_object_futures_with_pos_sizing()
        system = System(
            [rawdata, rules, posobject, combobject, capobject,
             Portfolios()], data, config)

        self.system = system
        self.config = config
        self.rules = rules
        self.rawdata = rawdata
        self.fcs = capobject
        self.forecast_combine = combobject
        self.data = data
        self.possizing = posobject
        self.portfolios = Portfolios

    def test_fixed_instrument_weights(self):
        ans = self.system.portfolio.get_instrument_weights()
        self.assertAlmostEqual(ans.BUND.values[-1], 0.2, places=2)
        self.assertAlmostEqual(ans.EDOLLAR.values[-1], 0.4, places=2)
        self.assertAlmostEqual(ans.US10.values[-1], 0.4, places=2)

    def test_estimated_instrument_weights(self):
        config = copy.copy(self.config)
        config.use_instrument_weight_estimates = True
        system2 = System([
            self.rawdata, self.rules, self.possizing, self.forecast_combine,
            self.fcs, Account(), self.portfolios()
        ], self.data, config)
        ans = system2.portfolio.get_instrument_weights()
        self.assertAlmostEqual(ans.BUND.values[-1], 0.541, places=2)
        self.assertAlmostEqual(ans.EDOLLAR.values[-1], 0.346, places=2)
        self.assertAlmostEqual(ans.US10.values[-1], 0.1121, places=2)

    def test_estimated_dm(self):
        config = copy.copy(self.config)
        config.use_instrument_weight_estimates = True
        system2 = System([
            self.rawdata, self.rules, self.possizing, self.forecast_combine,
            self.fcs, Account(), self.portfolios()
        ], self.data, config)
        ans = system2.portfolio.get_instrument_correlation_matrix().corr_list[
            -1]

        self.assertAlmostEqual(ans[0][1], 0.3889, places=3)
        self.assertAlmostEqual(ans[0][2], 0.5014, places=3)
        self.assertAlmostEqual(ans[1][2], 0.8771, places=3)

        ans = system2.portfolio.get_estimated_instrument_diversification_multiplier(
        )
        self.assertAlmostEqual(ans.values[-1], 1.1855, places=3)

    def test_get_fixed_instrument_diversification_multiplier(self):
        self.assertEqual(
            self.system.portfolio.
            get_fixed_instrument_diversification_multiplier().values[-1], 1.2)

    def test_get_notional_position(self):
        self.assertAlmostEqual(
            self.system.portfolio.get_notional_position("EDOLLAR").values[-1],
            1.2231,
            places=3)

    def test_get_position_method_buffer(self):
        self.assertAlmostEqual(
            self.system.portfolio.get_position_method_buffer("EDOLLAR").values[
                -1],
            0.12231,
            places=3)

    def test_get_forecast_method_buffer(self):
        self.assertAlmostEqual(
            self.system.portfolio.get_forecast_method_buffer("EDOLLAR").values[
                -1],
            0.496673,
            places=3)

    def test_get_buffers_for_position(self):
        ans = self.system.portfolio.get_buffers_for_position("EDOLLAR")
        self.assertAlmostEqual(ans.values[-1][0], 1.345424, places=3)
        self.assertAlmostEqual(ans.values[-1][1], 1.100802, places=3)

    def test_actual_positions(self):
        config = copy.copy(self.config)
        config.use_instrument_weight_estimates = True
        system2 = System([
            self.rawdata, self.rules, self.possizing, self.forecast_combine,
            self.fcs, Account(), self.portfolios()
        ], self.data, config)

        ans = system2.portfolio.get_actual_position("EDOLLAR")
        self.assertAlmostEqual(ans.values[-1], 1.058623, places=4)

        ans = system2.portfolio.get_actual_buffers_for_position("EDOLLAR")
        self.assertAlmostEqual(ans.values[-1][0], 1.164485, places=4)
        self.assertAlmostEqual(ans.values[-1][1], 0.952761, places=4)


if __name__ == "__main__":
    unittest.main()
