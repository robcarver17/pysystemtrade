import copy
import unittest

from systems.tests.testdata import get_test_object_futures_with_rules
from systems.basesystem import System
from systems.forecast_scale_cap import ForecastScaleCap


class Test(unittest.TestCase):
    def setUp(self):
        (rules, rawdata, data, config) = get_test_object_futures_with_rules()
        system = System([rawdata, rules, ForecastScaleCap()], data, config)
        self.system = system
        self.config = config
        self.rules = rules
        self.rawdata = rawdata
        self.forecast_scale_cap = ForecastScaleCap
        self.data = data

    def test_get_raw_forecast(self):
        ans = self.system.forecastScaleCap.get_raw_forecast(
            "EDOLLAR", "ewmac8").tail(1)
        self.assertAlmostEqual(ans.values[0], 0.164383, places=6)

    def test_get_forecast_cap(self):

        ans = self.system.forecastScaleCap.get_forecast_cap()
        self.assertEqual(ans, 21.0)

        ## test defaults
        config = self.config
        del (config.forecast_cap)
        system3 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        ans = system3.forecastScaleCap.get_forecast_cap()
        self.assertEqual(ans, 20.0)

    def test_get_forecast_scalar(self):
        # fixed
        ## From config
        self.assertEqual(
            self.system.forecastScaleCap.get_forecast_scalar(
                "EDOLLAR", "ewmac8"), 5.3)

        ## default
        config = copy.copy(self.config)
        unused = config.trading_rules['ewmac8'].pop('forecast_scalar')
        system2 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        self.assertEqual(
            system2.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8"),
            1.0)

        ## other config location
        setattr(config, 'forecast_scalars', dict(ewmac8=11.0))
        system3 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        self.assertEqual(
            system3.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8"),
            11.0)

        # estimated
        config = copy.copy(self.config)
        config.use_forecast_scale_estimates = True

        system2 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        ## From default
        self.assertAlmostEqual(
            system2.forecastScaleCap.get_forecast_scalar(
                "EDOLLAR", "ewmac8").tail(1).values[0],
            5.8,
            places=1)

        ## From config
        scale_config = dict(pool_instruments=False)
        config.forecast_scalar_estimate = scale_config
        system2 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        self.assertAlmostEqual(
            system2.forecastScaleCap.get_forecast_scalar(
                "EDOLLAR", "ewmac8").tail(1).values[0], 5.653444301)

    def test_get_scaled_forecast(self):

        self.assertAlmostEqual(
            self.system.forecastScaleCap.get_scaled_forecast(
                "EDOLLAR", "ewmac8").tail(1).values[0], 0.871230635)

    def test_get_capped_forecast(self):

        # fixed, normal cap
        self.assertAlmostEqual(
            self.system.forecastScaleCap.get_capped_forecast(
                "EDOLLAR", "ewmac8").tail(1).values[0], 0.871230635)

        # estimated, normal cap
        config = copy.copy(self.config)
        config.use_forecast_scale_estimates = True

        system2 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        self.assertAlmostEqual(
            system2.forecastScaleCap.get_forecast_scalar(
                "EDOLLAR", "ewmac8").tail(1).values[0],
            5.8,
            places=1)

        # binding cap
        config.use_forecast_scale_estimates = False
        config.forecast_cap = 0.2
        system3 = System([self.rawdata, self.rules, self.forecast_scale_cap()],
                         self.data, config)
        self.assertAlmostEqual(
            system3.forecastScaleCap.get_capped_forecast(
                "EDOLLAR", "ewmac8").tail(1).values[0], 0.2)


if __name__ == "__main__":
    unittest.main()
