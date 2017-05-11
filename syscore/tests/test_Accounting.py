'''
Created on 3 Dec 2015

@author: rob
'''
import unittest

import pandas as pd
import numpy as np

from syscore.accounting import pandl, get_positions_from_forecasts, get_trades_from_positions

dt_range1 = pd.date_range(start=pd.datetime(2014, 12, 30), periods=10)
dt_range2 = pd.date_range(start=pd.datetime(2015, 1, 1), periods=11)


class Test(unittest.TestCase):
    def test_get_positions_from_forecasts(self):
        fx = pd.DataFrame([2.0] * 10, dt_range1)
        price = pd.DataFrame(
            [100, 103, 105, 106, 110, 105, np.nan, 106, 120, np.nan,
             142], dt_range2)
        forecast = pd.DataFrame([
            np.nan, np.nan, np.nan, np.nan, 10.0, 10.0, 15.0, 15.0, 5.0, 0.0,
            -5.0
        ], dt_range2)
        value_of_price_point = 150.0

        daily_return_volatility = None
        position = get_positions_from_forecasts(
            price,
            daily_return_volatility,
            forecast,
            fx,
            value_of_price_point,
            min_periods=1)

        # TODO this has been divided by ten to what was here previously, error?
        expected_pos = [
            np.nan, np.nan, np.nan, np.nan, 252.34937866824254,
            90.572296272461699, 135.85844440869255, 135.85844440869255,
            24.878044993282998, 0.0, -24.878044993282995
        ]

        np.testing.assert_almost_equal(position.position.values, expected_pos)

    def test_get_trades_from_positions(self):
        positions = pd.DataFrame([np.nan, 2, 3, np.nan, 2, 3, 3.1, 4, 3, 5, 7],
                                 dt_range2)

        price = pd.DataFrame(
            [100, 103, np.nan, 106, 110, 105, np.nan, 106, 120, np.nan,
             142], dt_range2)

        # test delayed fill
        delayfill = True
        roundpositions = True
        get_daily_returns_volatility = None
        forecast = None
        fx = None
        value_of_price_point = None
        trades = get_trades_from_positions(
            price, positions, delayfill, roundpositions,
            get_daily_returns_volatility, forecast, fx, value_of_price_point)

        np.testing.assert_almost_equal(
            trades.trades, [2.0, 1.0, -1.0, 1.0, 1.0, -1.0, 2.0, 2.0])

        np.testing.assert_almost_equal(trades.fill_price[:-1], [
            106.0, 106.0, 105.0, 106.0, 120.0, 142.0, 142.0
        ])

        # test none delayed fill
        delayfill = False
        trades = get_trades_from_positions(
            price, positions, delayfill, roundpositions,
            get_daily_returns_volatility, forecast, fx, value_of_price_point)

        np.testing.assert_almost_equal(
            trades.trades, [2.0, 1.0, -1.0, 1.0, 1.0, -1.0, 2.0, 2.0])

        np.testing.assert_almost_equal(trades.fill_price, [
            103.0, 106.0, 110.0, 105.0, 106.0, 120.0, 142.0, 142.0
        ])

        # test roundpositions
        delayfill = True
        roundpositions = False
        trades = get_trades_from_positions(
            price, positions, delayfill, roundpositions,
            get_daily_returns_volatility, forecast, fx, value_of_price_point)

        np.testing.assert_almost_equal(
            trades.trades, [2.0, 1.0, -1.0, 1.0, 0.1, 0.9, -1.0, 2.0, 2.0])

        np.testing.assert_almost_equal(trades.fill_price[:-1], [
            106.0, 106.0, 105.0, 106.0, 106.0, 120.0, 142.0, 142.0
        ])

    def test_pandl(self):
        fx = pd.DataFrame([2.0] * 10, dt_range1)
        price = pd.DataFrame(
            [100, 103, 105, 106, 110, 105, 104.5, np.nan, 120, np.nan,
             142], dt_range2)

        trades = pd.concat([
            pd.DataFrame(
                dict(
                    trades=[2, 1, -1, np.nan, 1],
                    fill_price=[102.9, 105.5, 106.5, np.nan, 106.]),
                pd.date_range(start=pd.datetime(2015, 1, 2), periods=5)),
            pd.DataFrame(
                dict(trades=[-1, 1, -1], fill_price=[107, 119, 132]),
                pd.date_range(start=pd.datetime(2015, 1, 8), periods=3))
        ])

        ans = pandl(price, trades, marktomarket=True, fx=fx)
        np.testing.assert_almost_equal(ans.pandl_base[1:], [
            0.0, 10.4, 6., 14., -16., -9., 15., 48., 78., 40.
        ])

        ans2 = pandl(price, trades, marktomarket=False, fx=fx)

        np.testing.assert_almost_equal(ans2.pandl_base[1:],
                                       [10.4, 6., 0., -2., 6., 48., 78.])


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
