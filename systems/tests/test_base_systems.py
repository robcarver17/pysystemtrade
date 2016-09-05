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
        data = Data()
        stage._protected = ["protected"]

        system = System([stage], data, None)
        print(system._cache)

        system.set_item_in_cache(3, ("test", "a"), "US10")
        print(system._cache)

        self.assertEqual(system.get_item_from_cache(("test", "a"), "US10"), 3)

        def afunction(system, instrument_code, stage,
                      wibble, another_wibble=10):
            return instrument_code + wibble + str(another_wibble) + stage.name

        def anestedfunction(system, instrument_code,
                            keyname, stage, wibble, another_wibble=10):
            return instrument_code + wibble + keyname + \
                str(another_wibble) + stage.name

        ans = system.calc_or_cache("b", "c", afunction, stage, "d")
        print(system._cache)

        ans = system.calc_or_cache("b", "c", afunction, stage, "d", 20.0)
        print(system._cache)

        ans = system.calc_or_cache_nested(
            "c", "SP500", "thing", anestedfunction, stage, "k")
        print(system._cache)

        ans = system.calc_or_cache(
            "b", ALL_KEYNAME, afunction, stage, "e", 120.0)
        print(system._cache)

        ans = system.calc_or_cache(
            "protected", ALL_KEYNAME, afunction, stage, "e", 120.0)

        ans = system.get_item_from_cache(("test""c"), "SP500", "thing")
        print(system._cache)

        system._delete_item_from_cache(("test", "b"), "c")
        print(system._cache)

        ans = system.set_item_in_cache(10.0, ("test", "protected"), "SP500")
        print(system._cache)

        print(system.get_item_from_cache(("test", "b"), ALL_KEYNAME))

        ans = system.set_item_in_cache("protected", ("test2", 10.0), "SP500")

        print(system._cache)

        print(system.get_items_across_system())
        print(system.get_items_with_data())
        print(system.get_protected_items())
        print(system.get_items_for_instrument("SP500"))
        print(system.get_itemnames_for_stage("test"))

        system.delete_items_for_stage("test2")

        print(system._cache)

        system.delete_items_across_system()

        print(system._cache)

        system.delete_items_across_system(True)

        print(system._cache)

        system.delete_items_for_instrument("SP500")
        print(system._cache)

        system.delete_items_for_instrument("SP500", True)
        print(system._cache)

        system.delete_item(("test", "a"))

        print(system._cache)

        # TODO assert not print

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
