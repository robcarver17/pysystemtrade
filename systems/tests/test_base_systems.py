'''
Created on 14 Dec 2015

@author: rob
'''
import unittest
from systems.stage import SystemStage
from systems.basesystem import System, ALL_KEYNAME
from sysdata.data import Data

class Test(unittest.TestCase):

    def testName(self):
        stage = SystemStage()
        stage.name = "test"
        data=Data()
        stage._protected = ["protected"]

        system = System([stage], data, None)
        print(system._cache)

        system.set_item_in_cache(3, "a", "US10")
        print(system._cache)

        self.assertEqual(system.get_item_from_cache("a", "US10"), 3)

        def afunction(system, instrument_code, wibble, another_wibble=10):
            return instrument_code + wibble + str(another_wibble)

        def anestedfunction(system, instrument_code,
                            keyname, wibble, another_wibble=10):
            return instrument_code + wibble + keyname + str(another_wibble)

        ans = system.calc_or_cache("b", "c", afunction, "d")
        print(system._cache)

        ans = system.calc_or_cache("b", "c", afunction, "d", 20.0)
        print(system._cache)

        ans = system.calc_or_cache_nested(
            "c", "SP500", "thing", anestedfunction, "k")
        print(system._cache)

        ans = system.calc_or_cache("b", ALL_KEYNAME, afunction, "e", 120.0)
        print(system._cache)

        ans = system.calc_or_cache(
            "protected", ALL_KEYNAME, afunction, "e", 120.0)

        ans = system.get_item_from_cache("c", "SP500", "thing")
        print(system._cache)

        system._delete_item_from_cache("b", "c")
        print(system._cache)

        ans = system.set_item_in_cache(10.0, "protected", "SP500")
        print(system._cache)

        print(system.get_item_from_cache("b", ALL_KEYNAME))

        print(system.get_items_across_system())
        print(system.get_items_with_data())
        print(system.get_protected_items())
        print(system.get_items_for_instrument("SP500"))

        system.delete_items_across_system()

        print(system._cache)

        system.delete_items_across_system(True)

        print(system._cache)

        system.delete_items_for_instrument("SP500")
        print(system._cache)

        system.delete_items_for_instrument("SP500", True)
        print(system._cache)

        system.delete_item("a")

        print(system._cache)

        # TODO assert not print

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
