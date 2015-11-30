'''
Created on 27 Nov 2015

@author: rob
'''
import unittest
from sysdata.data import Data
from syscore.objects import calc_or_cache, calc_or_cache_nested

class Test(unittest.TestCase):


    def testName(self):
        
        data=Data()
        somedict=dict(a=2)
        setattr(data, "somedict", somedict)
        def a_function(someobject, keyname, blah, wibble=30):
             return(keyname+" "+str(blah)+" "+str(wibble))
        
        self.assertEqual(calc_or_cache(data, "somedict", "a", a_function, 99, wibble=10), 2)
         
        self.assertEqual(calc_or_cache(data, "somedict", "b", a_function, 99, wibble=10), 'b 99 10')
        
        self.assertEqual(data.somedict['b'], 'b 99 10')

        somedict=dict(a=dict(b=2))
        setattr(data, "somedict", somedict)
        
        def another_function(someobject, keyname1, keyname2, blah, wibble=30):
             return(keyname1+" "+keyname2+" "+str(blah)+" "+str(wibble))

        self.assertEqual(calc_or_cache_nested(data, "somedict", "a", "b", another_function, 99, wibble=10), 2)
         
        self.assertEqual(calc_or_cache_nested(data, "somedict", "a", "c", another_function, 99, wibble=10), 'a c 99 10')
        
        self.assertEqual(data.somedict['a']['c'], 'a c 99 10')

        self.assertEqual(calc_or_cache_nested(data, "somedict", "b", "c", another_function, 99, wibble=10), 'b c 99 10')


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    