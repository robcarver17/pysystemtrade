import unittest
from systems.tests.testdata import get_test_object
from systems.basesystem import System


class Test(unittest.TestCase):
    def setUp(self):

        (rawdata, data, config) = get_test_object()

        system = System([rawdata], data)
        self.system = system

    def test_daily_denominator_price(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_denominator_price("EDOLLAR").tail(1)
            .values[0], 97.9875)

    def test_daily_returns(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_returns("EDOLLAR").tail(1).values[0],
            0.1075)

    def test_daily_returns_volatility(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_returns_volatility("EDOLLAR").tail(1)
            .values[0],
            0.058522,
            places=6)

    def test_daily_percentage_volatility(self):
        self.assertAlmostEqual(
            self.system.rawdata.get_daily_percentage_volatility("EDOLLAR")
            .tail(1).values[0],
            0.059789,
            places=6)

    def test_norm_returns(self):
        self.assertAlmostEqual(
            self.system.rawdata.norm_returns("EDOLLAR").tail(1).values[0],
            1.985413,
            places=6)


if __name__ == "__main__":
    unittest.main()
