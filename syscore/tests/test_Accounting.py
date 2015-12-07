'''
Created on 3 Dec 2015

@author: rob
'''
import unittest

import pandas as pd
import numpy as np

from syscore.accounting import pandl, get_positions_from_forecasts, get_trades_from_positions 

class Test(unittest.TestCase):


    def test_get_positions_from_forecasts(self):
        fx=pd.DataFrame([2.0]*10 , pd.date_range(start=pd.datetime(2014,12,30), periods=10))
        price=   pd.DataFrame([100,    103,    105,    106,   110,  105,  np.nan, 106, 120, np.nan, 142], pd.date_range(start=pd.datetime(2015,1,1), periods=11))
        forecast=pd.DataFrame([np.nan, np.nan, np.nan, np.nan,10.0, 10.0, 15.0,   15.0, 5.0, 0.0, -5.0], pd.date_range(start=pd.datetime(2015,1,1), periods=11))
        value_of_price_point=150.0
        position=get_positions_from_forecasts(price, None, forecast, fx, value_of_price_point, min_periods=1)

        self.assertAlmostEqual(list(position.position.values)[4:], [2523.4937866824253, 905.72296272461699, 1358.5844440869255, 1358.5844440869255, 248.78044993282995, 0.0, -248.78044993282995])

    def test_get_trades_from_positions(self):
        positions= pd.DataFrame([np.nan,   2,    3,      np.nan,     2,     3,   3.1,     4,    3,      5,      7], pd.date_range(start=pd.datetime(2015,1,1), periods=11))
        price=     pd.DataFrame([100,    103,    np.nan,    106,     110,  105,  np.nan, 106, 120, np.nan, 142], pd.date_range(start=pd.datetime(2015,1,1), periods=11))        
        #trades=get_trades_from_positions(price, positions, delayfill, roundpositions, None, None, None, None)
        trades=get_trades_from_positions(price, positions, True, True,                 None, None, None, None)
        
        self.assertEqual(list(trades.trades), [2.0, 1.0, -1.0, 1.0, 1.0, -1.0, 2.0, 2.0])
        self.assertEqual(list(trades.fill_price)[:-1], [106.0, 106.0, 105.0, 106.0, 120.0, 142.0, 142.0])


        trades=get_trades_from_positions(price, positions, False, True,                 None, None, None, None)

        self.assertEqual(list(trades.trades), [2.0, 1.0, -1.0, 1.0, 1.0, -1.0, 2.0, 2.0])
        self.assertEqual(list(trades.fill_price), [103.0, 106.0, 110.0, 105.0, 106.0, 120.0, 142.0, 142.0])


        trades=get_trades_from_positions(price, positions, True, False,                 None, None, None, None)

        self.assertEqual(list(trades.trades), [2.0, 1.0, -1.0, 1.0, 0.1, 0.9,  -1.0, 2.0, 2.0])
        self.assertEqual(list(trades.fill_price)[:-1], [106.0, 106.0, 105.0, 106.0, 106.0, 120.0, 120.0, 142.0, 142.0])

    def test_pandl(self):
        fx=pd.DataFrame([2.0]*10 , pd.date_range(start=pd.datetime(2014,12,30), periods=10))
        price=   pd.DataFrame(                    [100,    103,    105,    106,   110,     105,    104.5, 
                                                   np.nan,     120, np.nan, 142], pd.date_range(start=pd.datetime(2015,1,1), periods=11))
        trades=pd.concat([pd.DataFrame(dict(trades=[        2,       1,      -1,  np.nan,  1        ],
                                        fill_price=[        102.9,  105.5, 106.5,  np.nan,  106.]),
                                       pd.date_range(start=pd.datetime(2015,1,2), periods=5)),
                         pd.DataFrame(dict(trades=[  -1,     1,      -1], 
                                   fill_price=     [ 107,    119,    132   ]), pd.date_range(start=pd.datetime(2015,1,8), periods=3))])
      
        
        ans=pandl(price, trades, marktomarket=True, fx=fx)
        self.assertEqual(list(ans.pandl_base)[1:], [0.0, 10.4, 6.,14., -16., -9., 15., 48., 78., 40.])

        ans2=pandl(price, trades, marktomarket=False, fx=fx)
        self.assertEqual(list(ans2.pandl_base)[1:], [ 10.4, 6., 0., -2., 6., 48., 78.])
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()