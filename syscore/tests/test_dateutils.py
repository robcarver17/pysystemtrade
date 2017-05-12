'''
Created on 27 Nov 2015

@author: rob
'''
import unittest as ut
import numpy as np
import pandas as pd

from syscore.dateutils import expiry_diff


class Test(ut.TestCase):
    def test_data(self):
        x = pd.DataFrame(
            dict(
                CARRY_CONTRACT=
                ["", "201501", "", "201501", "20150101", "20150101", "201501"],
                PRICE_CONTRACT=
                ["", "", "201504", "201504", "201504", "20150115", "201406"]))

        return x

    def test_expiry_diff(self):
        x = self.test_data()
        expiries = x.apply(expiry_diff, 1)
        expected = [
            -0.24640657084188911, -0.24640657084188911, -0.054757015742642023,
            0.58590006844626963
        ]
        self.assertTrue(all([np.isnan(y) for y in expiries[:3]]))
        for (got, wanted) in zip(expiries[3:], expected):
            self.assertAlmostEqual(got, wanted)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_robust_vol_calc']
    ut.main()
