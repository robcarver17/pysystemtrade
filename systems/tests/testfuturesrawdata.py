import numpy as np
from systems.futures.rawdata import FuturesRawData
from systems.basesystem import System
from sysdata.csvdata import csvFuturesData
from sysdata.configdata import Config
import unittest


def get_test_object_futures():
    """
    Returns some standard test data
    """
    data = csvFuturesData("sysdata.tests")
    config = Config("systems.provided.example.exampleconfig.yaml")
    rawdata = FuturesRawData()
    return (rawdata, data, config)


class Test(unittest.TestCase):
    def setUp(self):

        (rawdata, data, config) = get_test_object_futures()

        system = System([rawdata], data, config)
        self.system = system

    def test_get_instrument_raw_carry_data(self):
        carry_values = self.system.rawdata.get_instrument_raw_carry_data(
            "EDOLLAR").tail(1)
        self.assertEqual(carry_values.PRICE.values[0], 97.9875)
        self.assertTrue(np.isnan(carry_values.CARRY.values[0]))
        self.assertEqual(carry_values.CARRY_CONTRACT.values[0], '201812')
        self.assertEqual(carry_values.PRICE_CONTRACT.values[0], '201903')

    def test_raw_futures_roll(self):
        self.assertAlmostEqual(
            self.system.rawdata.raw_futures_roll("EDOLLAR").ffill().tail(1)
            .values[0], -0.07)

    def test_roll_differentials(self):
        self.assertAlmostEqual(
            self.system.rawdata.roll_differentials("EDOLLAR").ffill().tail(1)
            .values[0],
            -0.246407,
            places=6)

    def test_annualised_roll(self):
        self.assertAlmostEqual(
            self.system.rawdata.annualised_roll("EDOLLAR").ffill().tail(1)
            .values[0],
            0.284083,
            places=6)

    def test_daily_annualised_roll(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_annualised_roll("EDOLLAR").ffill().tail(
                1).values[0],
            0.284083,
            places=6)

    def test_daily_denominator_price(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_denominator_price("EDOLLAR").ffill()
            .tail(1).values[0],
            97.9875,
            places=6)


if __name__ == "__main__":
    unittest.main()
