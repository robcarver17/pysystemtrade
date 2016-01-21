'''
Created on 20 Jan 2016



@author: rob
'''
import unittest
import numpy as np
from systems.tests.testdata import get_test_object_futures_with_rules_and_capping_estimate
from systems.basesystem import System
from systems.forecast_combine import ForecastCombineEstimated

class Test(unittest.TestCase):


    def setUp(self):
        (fcs, rules, rawdata, data, config)=get_test_object_futures_with_rules_and_capping_estimate()
        system=System([rawdata, rules, fcs, ForecastCombineEstimated()], data, config)
        setattr(self, "system", system)


    def tearDown(self):
        self.system.delete_all_items(delete_protected=True)

    
    def testDefaults(self):
        instrument_code="EDOLLAR"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[0][0][1], 0.99, places=5)
        print(ans.columns)

        instrument_code="US10"
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.03850942, places=5)
        print(ans.columns)
        
        instrument_code="BUND"
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.88423735, places=5)
        print(ans.columns)

    """
    def testPooling(self):
        self.system.config.forecast_correlation_estimate['pool_instruments']="False"
        
        instrument_code="EDOLLAR"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], -0.06487642, places=5)
        print(ans.columns)
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.18177671, places=5)
        print(ans.columns)
        
    def testFrequency(self):

        self.system.config.forecast_correlation_estimate['frequency']="D"
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.22036673, places=5)
        
    def testDatemethod(self):
        self.system.config.forecast_correlation_estimate['date_method']="rolling"
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.04097480, places=5)
        
    def testExponent(self):
        self.system.config.forecast_correlation_estimate['using_exponent']="False"
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        print(ans)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.12906539, places=5)

    def testExponentLookback(self):
        self.system.config.forecast_correlation_estimate['ew_lookback']=50
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[-1][0][1], 0.12842128, places=5)

    def testminperiods(self):
        self.system.config.forecast_correlation_estimate['pool_instruments']="False"
        self.system.config.forecast_correlation_estimate['min_periods']=500
        instrument_code="US10"
        
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertAlmostEqual(ans.corr_list[9][0][1], 0.99, places=5)
        self.assertAlmostEqual(ans.corr_list[10][0][1], 0.1746773, places=5)
    """
    def testnotcleaning(self):
        self.system.config.forecast_correlation_estimate['cleaning']="False"
        self.system.config.forecast_correlation_estimate['pool_instruments']="False"
        self.system.config.forecast_correlation_estimate['min_periods']=5000

        instrument_code="US10"
        ans=self.system.combForecast.get_forecast_correlation_matrices(instrument_code)
        self.assertTrue(np.isnan(ans.corr_list[0][0][0]))
        self.assertTrue(np.isnan(ans.corr_list[1][0][0]))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()