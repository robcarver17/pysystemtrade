import numpy as np
from systems.futures.rawdata import FuturesRawData
from systems.basesystem import System
from sysdata.csv.csv_sim_futures_data import csvFuturesSimData
from sysdata.configdata import Config
import unittest


def get_test_object_futures():
    """
    Returns some standard test data
    """
    data = csvFuturesSimData(
        datapath_dict=dict(
            config_data="sysdata.tests.configtestdata",
            adjusted_prices="sysdata.tests.multiplepricestestdata",
            spot_fx_data="sysdata.tests.fxtestdata",
            multiple_price_data="sysdata.tests.multiplepricestestdata",
        )
    )
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
            "EDOLLAR"
        ).tail(1)
        self.assertEqual(carry_values.PRICE.values[0], 97.4425)
        self.assertTrue(np.isnan(carry_values.CARRY.values[0]))
        self.assertEqual(carry_values.CARRY_CONTRACT.values[0], "20210300")
        self.assertEqual(carry_values.PRICE_CONTRACT.values[0], "20210600")

    def test_raw_futures_roll(self):
        self.assertAlmostEqual(self.system.rawdata.raw_futures_roll(
            "EDOLLAR").ffill().tail(1).values[0], -0.015, )

    def test_roll_differentials(self):
        self.assertAlmostEqual(self.system.rawdata.roll_differentials(
            "EDOLLAR").ffill().tail(1).values[0], -0.2518823, places=6, )

    def test_annualised_roll(self):
        self.assertAlmostEqual(self.system.rawdata.annualised_roll(
            "EDOLLAR").ffill().tail(1).values[0], 0.059551, places=4, )

    def test_daily_annualised_roll(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_annualised_roll("EDOLLAR")
            .ffill()
            .tail(1)
            .values[0],
            0.05955163,
            places=4,
        )

    def test_daily_denominator_price(self):
        self.assertAlmostEqual(
            self.system.rawdata.daily_denominator_price("EDOLLAR")
            .ffill()
            .tail(1)
            .values[0],
            97.4425,
            places=4,
        )


if __name__ == "__main__":
    unittest.main()
