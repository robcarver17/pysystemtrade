import copy
import unittest

from systems.account import Account
from systems.basesystem import System
from systems.tests.testdata import get_test_object_futures_with_rules_and_capping

@unittest.SkipTest
class Test(unittest.TestCase):
    def setUp(self):

        (
            fcs,
            rules,
            rawdata,
            data,
            config,
        ) = get_test_object_futures_with_rules_and_capping()
        system = System(
            [rawdata, rules, fcs, ForecastCombineMaybeThreshold()], data, config
        )

        self.system = system
        self.config = config
        self.rules = rules
        self.rawdata = rawdata
        self.fcs = fcs
        self.forecast_combine = ForecastCombine
        self.data = data

    def test_get_combined_forecast(self):
        # this is default, but be explicit
        self.config.instruments_with_threshold = []
        fdf = self.system.combForecast.get_combined_forecast("EDOLLAR")
        assert fdf.max() < 30
        assert fdf.min() > -30
        # fdf.describe()
        # count    8395.000000
        # mean        4.502549
        # std        13.173807
        # min       -21.000000
        # 25%        -5.705687
        # 50%         6.456878
        # 75%        16.528847
        # max        21.000000

    def test_get_combined_threshold_forecsat(self):
        # modify config in place
        self.config.instruments_with_threshold = ["EDOLLAR", "BUND"]
        fdf = self.system.combForecast.get_combined_forecast("EDOLLAR")
        assert fdf.max() == 30
        assert fdf.min() == -30
        self.config.instruments_with_threshold = []
        # fdf.describe()
        # count    8395.000000
        # mean        5.298001
        # std        16.459646
        # min       -30.000000
        # 25%         0.000000
        # 50%         0.000000
        # 75%        19.586541
        # max        30.000000

    def test_get_capped_forecast(self):

        self.assertAlmostEqual(
            self.system.combForecast.get_capped_forecast("EDOLLAR", "ewmac8")
            .tail(1)
            .values[0],
            0.8712306,
        )

    def test_get_forecast_cap(self):
        self.assertEqual(self.system.combForecast.get_forecast_cap(), 21.0)

    def test_get_trading_rule_list(self):

        # fixed weights
        ans = self.system.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans, ["ewmac16", "ewmac8"])

        ans2 = self.system.combForecast.get_trading_rule_list("BUND")
        self.assertEqual(ans2, ["ewmac8"])

        # fixed weights - non nested dict
        config = copy.copy(self.config)
        config.forecast_weights = dict(ewmac8=0.5, ewmac16=0.5)
        system2 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans3 = system2.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans3, ["ewmac16", "ewmac8"])
        ans4 = system2.combForecast.get_trading_rule_list("BUND")
        self.assertEqual(ans4, ans3)

        # fixed weights - missing
        del config.forecast_weights
        system3 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans5 = system3.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans5, ["ewmac16", "ewmac8"])

        # estimated weights - missing
        config.use_forecast_weight_estimates = True
        system4 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans6 = system4.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans6, ["ewmac16", "ewmac8"])

        # estimated weights - non nested
        setattr(config, "rule_variations", ["ewmac8"])
        system5 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans6 = system5.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans6, ["ewmac8"])

        # estimated weights - nested dict
        setattr(
            config,
            "rule_variations",
            dict(
                EDOLLAR=["ewmac8"],
                BUND=["ewmac16"],
                US10=[
                    "ewmac8",
                    "ewmac16"]),
        )
        system6 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans7 = system6.combForecast.get_trading_rule_list("EDOLLAR")
        self.assertEqual(ans7, ["ewmac8"])
        ans8 = system6.combForecast.get_trading_rule_list("BUND")
        self.assertEqual(ans8, ["ewmac16"])
        ans8 = system6.combForecast.get_trading_rule_list("US10")
        self.assertEqual(ans8, ["ewmac16", "ewmac8"])  # missing

    def test_has_same_rules_as_code(self):

        ans = self.system.combForecast.has_same_rules_as_code("EDOLLAR")
        self.assertEqual(ans, ["EDOLLAR", "US10"])

        ans2 = self.system.combForecast.has_same_rules_as_code("BUND")
        self.assertEqual(ans2, ["BUND"])

    def test_get_all_forecasts(self):

        ans = self.system.combForecast.get_all_forecasts("EDOLLAR")
        self.assertAlmostEqual(ans.ewmac16.values[-1], 3.6062425)

        ans2 = self.system.combForecast.get_all_forecasts("BUND")
        self.assertAlmostEqual(ans2.ewmac8.values[-1], -0.276206423)

    def test_get_raw_fixed_forecast_weights(self):

        # fixed weights:
        #    nested dict (in config)
        ans1a = self.system.combForecast.get_forecast_weights("EDOLLAR")
        self.assertAlmostEqual(ans1a.ewmac16.values[-1], 0.5)

        ans1b = self.system.combForecast.get_raw_monthly_forecast_weights("BUND")
        self.assertEqual(ans1b.ewmac8.values[-1], 1.0)

        #    missing; equal weights
        config = copy.copy(self.config)
        del config.forecast_weights
        system2 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans2 = system2.combForecast.get_forecast_weights("BUND")
        self.assertAlmostEqual(ans2.ewmac8.values[-1], 0.49917057)  # smoothing

        #    non nested dict
        config.forecast_weights = dict(ewmac8=0.1, ewmac16=0.9)
        system3 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine()],
            self.data,
            config,
        )
        ans3 = system3.combForecast.get_forecast_weights("BUND")
        self.assertEqual(ans3.ewmac8.values[-1], 0.099834114877206212)

    def setUpWithEstimatedReturns(self):
        config = copy.copy(self.config)
        config.use_forecast_weight_estimates = True
        config.use_forecast_div_mult_estimates = True
        new_system = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine(), Account()],
            self.data,
            config,
        )

        return new_system

    def test_get_returns_for_optimisation(self):
        # Note: More thorough tests will be run inside optimisation module
        # (FIXME next refactoring) At this point we don't run proper tests but
        # just check all the plumbing works with new caching code
        # FIXME rewrite proper tests once refactored optimisation generally

        system = self.setUpWithEstimatedReturns()

        print(
            system.combForecast.get_SR_cost_for_instrument_forecast(
                "EDOLLAR", "ewmac8"))
        print(
            system.combForecast.get_SR_cost_for_instrument_forecast(
                "BUND", "ewmac8"))
        print(
            system.combForecast.get_SR_cost_for_instrument_forecast(
                "US10", "ewmac8"))

        print(system.combForecast.has_same_cheap_rules_as_code("EDOLLAR"))
        print(system.combForecast.has_same_cheap_rules_as_code("BUND"))
        print(system.combForecast.has_same_cheap_rules_as_code("US10"))

        print(system.combForecast.get_returns_for_optimisation("EDOLLAR").to_frame())
        print(system.combForecast.get_returns_for_optimisation("BUND").to_frame())
        print(system.combForecast.get_returns_for_optimisation("US10").to_frame())

        print(system.combForecast.has_same_cheap_rules_as_code("EDOLLAR"))
        print(system.combForecast.has_same_cheap_rules_as_code("BUND"))
        print(system.combForecast.has_same_cheap_rules_as_code("US10"))

        # default - don't pool costs, pool gross
        print(system.combForecast.get_raw_monthly_forecast_weights("BUND"))

        # pool neither gross or costs
        config = copy.copy(system.config)
        config.forecast_weight_estimate["pool_gross_returns"] = False
        config.forecast_weight_estimate["forecast_cost_estimates"] = False

        system2 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine(), Account()],
            self.data,
            config,
        )
        print(system2.combForecast.get_raw_monthly_forecast_weights("BUND"))

        # pool gross, not costs
        config = copy.copy(system.config)
        config.forecast_weight_estimate["pool_gross_returns"] = True
        config.forecast_weight_estimate["forecast_cost_estimates"] = False

        system2 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine(), Account()],
            self.data,
            config,
        )
        print(system2.combForecast.get_raw_monthly_forecast_weights("BUND"))

        # pool both (special function)
        config = copy.copy(system.config)
        config.forecast_weight_estimate["pool_gross_returns"] = True
        config.forecast_weight_estimate["forecast_cost_estimates"] = True

        system2 = System(
            [self.rawdata, self.rules, self.fcs, self.forecast_combine(), Account()],
            self.data,
            config,
        )
        print(system2.combForecast.get_raw_monthly_forecast_weights("BUND"))

    def test_fixed_fdm(self):
        print(self.system.combForecast.get_monthly_forecast_diversification_multiplier("BUND"))

    def test_estimated_fdm(self):
        system = self.setUpWithEstimatedReturns()
        print(system.combForecast.get_monthly_forecast_diversification_multiplier("BUND"))


if __name__ == "__main__":
    unittest.main()
