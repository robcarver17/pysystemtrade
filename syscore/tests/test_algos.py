'''
Created on 27 Nov 2015

@author: rob
'''
import unittest as ut
import numpy as np

from syscore.pdutils import pd_readcsv_frompackage
from syscore.algos import robust_vol_calc


class Test(ut.TestCase):

    def test_robust_vol_calc(self):
        prices = pd_readcsv_frompackage(
            "syscore", "pricetestdata.csv", ["tests"])
        returns = prices.diff()
        vol = robust_vol_calc(returns, days=35)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.41905275480464305)

        vol = robust_vol_calc(returns, days=100)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.43906619578902956)

    def test_robust_vol_calc_min_period(self):
        prices = pd_readcsv_frompackage(
            "syscore", "pricetestdata_min_period.csv", ["tests"])
        returns = prices.diff()
        vol = robust_vol_calc(returns, min_periods=9)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.45829858614978286)
        vol = robust_vol_calc(returns, min_periods=10)
        self.assertTrue(np.isnan(vol.iloc[-1][0]))

    def test_robust_vol_calc_min_value(self):
        prices = pd_readcsv_frompackage(
            "syscore", "pricetestdata_zero_vol.csv", ["tests"])
        returns = prices.diff()
        vol = robust_vol_calc(returns, vol_abs_min=0.01)
        self.assertEqual(vol.iloc[-1, 0], 0.01)

    def test_robust_vol_calc_floor(self):
        prices = pd_readcsv_frompackage(
            "syscore", "pricetestdata_vol_floor.csv", ["tests"])
        returns = prices.diff()
        vol = robust_vol_calc(returns)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.54492982003602064)
        vol = robust_vol_calc(returns, vol_floor=False)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.42134038479240132)
        vol = robust_vol_calc(returns, floor_min_quant=.5)
        self.assertAlmostEqual(vol.iloc[-1, 0], 1.6582199589924964)
        vol = robust_vol_calc(returns, floor_min_periods=500)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.42134038479240132)
        vol = robust_vol_calc(returns, floor_days=10, floor_min_periods=5)
        self.assertAlmostEqual(vol.iloc[-1, 0], 0.42134038479240132)

"""
    def test_calc_ewmac_forecast(self):
        prices=pd_readcsv_frompackage("syscore", "pricetestdata.csv", ["tests"])
        fcast=calc_ewmac_forecast(prices, 2, 8)
        self.assertAlmostEqual(fcast.iloc[-1][0],-0.58728633970596145)
        fcast=calc_ewmac_forecast(prices, 100, 500)
        self.assertAlmostEqual(fcast.iloc[-1][0],20.914172249098829)
        self.assertEqual(fcast.shape, (528,1))
"""

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_robust_vol_calc']
    ut.main()
