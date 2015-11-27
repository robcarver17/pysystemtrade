'''
Created on 19 Nov 2015

@author: rob
'''
import unittest
from syscore.dateutils import expiryDate
import pandas as pd
import datetime 

class Test(unittest.TestCase):


    def testexpiryDate(self):

        self.assertEqual(expiryDate("20140101"), pd.datetime(2014,1,1))
        self.assertEqual(expiryDate("201401"), pd.datetime(2014,1,1))
        self.assertEqual(expiryDate(pd.datetime(2014,1,1)), pd.datetime(2014,1,1))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()