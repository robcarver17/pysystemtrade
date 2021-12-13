from systems.tests.testdata import get_test_object
from systems.basesystem import System
import unittest


class Test(unittest.TestCase):
    def setUp(self):

        (rawdata, data, config) = get_test_object()

        system = System([rawdata], data)
        self.system = system

    @unittest.SkipTest
    def test_daily_denominator_price(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_denominator_price("EDOLLAR").tail(1).values[0],
            97.4425,
            places=4,
        )

    @unittest.SkipTest
    def test_daily_returns(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_returns("EDOLLAR").tail(1).values[0], -0.0225
        )

    @unittest.SkipTest
    def test_daily_returns_volatility(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_returns_volatility("EDOLLAR").tail(1).values[0],
            0.03327772,
            places=6,
        )

    @unittest.SkipTest
    def test_daily_percentage_volatility(self):
        self.assertAlmostEqual(
            self.system.rawdata.get_daily_percentage_volatility("EDOLLAR")
            .tail(1)
            .values[0],
            0.034143,
            places=6,
        )

    @unittest.SkipTest
    def test_norm_returns(self):
        self.assertAlmostEqual(
            self.system.rawdata.get_daily_vol_normalised_returns("EDOLLAR")
            .tail(1)
            .values[0],
            -0.67556593,
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
