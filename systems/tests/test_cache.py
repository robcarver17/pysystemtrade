import unittest

from systems.stage import SystemStage
from systems.basesystem import System
from systems.system_cache import input, diagnostic, output, ALL_KEYNAME
from sysdata.data import Data
from sysdata.configdata import Config


class testStage1(SystemStage):
    def _name(self):
        return "test_stage1"

    @diagnostic()
    def single_instrument_no_keywords(self, instrument_code):
        return 5

    @diagnostic()
    def single_instrument_with_keywords(self, instrument_code, keyword):
        return 6

    @diagnostic()
    def single_instrument_with_keywords_and_flags(self,
                                                  instrument_code,
                                                  keyword,
                                                  x_flag=3):
        return (7, x_flag)

    @output()
    def across_markets_no_keywords(self):
        return 9

    @diagnostic(not_pickable=True)
    def single_instrument_not_pickable(self):
        return 10

    @output(protected=True)
    def single_instrument_protected(self, instrument_code):
        return 11

    @output(protected=True)
    def across_markets_protected(self):
        return 12


class testStage2(SystemStage):
    def _name(self):
        return "test_stage2"

    @input
    def input2_stage_no_caching(self, x):
        return x

    @diagnostic()
    def single2_instrument_no_keywords(self, instrument_code):
        return 14

    @diagnostic()
    def single_instrument_with_keywords(self, instrument_code, variation_name):
        ## deliberate duplicate
        return 15


class TestCache(unittest.TestCase):
    def setUp(self):

        system = System(
            [testStage1(), testStage2()],
            Data(),
            Config(dict(instruments=["code", "another_code"])))
        self.system = system

    def test_get_instrument_list(self):
        self.system.get_instrument_list()
        self.system.get_instrument_list()
        self.assertEqual(len(self.system.cache.get_items_with_data()), 1)

    def test_stage_input_wrapper(self):
        ## this shouldn't cache
        not_used = self.system.test_stage2.input2_stage_no_caching(5.0)
        ## check cache still empty
        self.assertEqual(len(self.system.cache.get_items_with_data()), 0)

    def test_single_instrument_no_keywords(self):

        self.system.test_stage1.single_instrument_no_keywords("code")
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual(cache_ref.instrument_code, "code")
        self.assertEqual(self.system.cache[cache_ref].value(), 5)
        self.assertEqual(len(self.system.cache._get_pickable_items()),
                         2)  # includes cache of instrument list
        self.assertEqual(len(self.system.cache._get_protected_items()), 0)

        cache_ref_list = self.system.cache.get_items_with_data()

        ## no protected, so should still have two elements inside
        self.assertEqual(
            len(
                self.system.cache.cache_ref_list_with_protected_removed(
                    cache_ref_list)), 2)

        self.system.cache.delete_all_items()

        ## not protected so deletion should work
        self.assertEqual(len(self.system.cache.get_items_with_data()), 0)

    def test_single_instrument_with_keywords(self):

        self.system.test_stage1.single_instrument_with_keywords(
            "code", "keyname")
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual(cache_ref.instrument_code, "code")
        self.assertEqual(cache_ref.keyname, "keyname")
        self.assertEqual(self.system.cache[cache_ref].value(), 6)

    def test_single_instrument_with_keywords_and_flags(self):
        self.system.test_stage1.single_instrument_with_keywords_and_flags(
            "code", "keyname", x_flag=True)
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual(cache_ref.instrument_code, "code")
        self.assertEqual(cache_ref.keyname, "keyname")
        self.assertEqual(self.system.cache[cache_ref].value(), (7, True))
        self.assertEqual(cache_ref.flags, "x_flag=True")

    def test_across_markets_no_keywords(self):
        ans = self.system.test_stage1.across_markets_no_keywords()
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual(cache_ref.instrument_code, ALL_KEYNAME)
        self.assertEqual(cache_ref.keyname, "")

        ans = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(len(ans),
                         2)  ## also includes base_system.get_instrument_list()

        # test deletion across ...
        self.system.test_stage1.single_instrument_no_keywords(
            "code")  ## this shouldn't be deleted ...
        self.system.cache.delete_items_across_system()  # ... when we do this

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 1)
        cache_ref = cache_refs[0]
        self.assertEqual(cache_ref.itemname, "single_instrument_no_keywords")

        # incidentally should also wipe out this guy
        cache_refs = self.system.cache.get_cacherefs_for_stage(
            self.system.name)
        self.assertEqual(len(cache_refs), 0)

    def test_pickling(self):
        ans = self.system.test_stage1.across_markets_no_keywords()
        ans2 = self.system.test_stage1.single_instrument_not_pickable()

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 2)

        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(len(cache_refs), 3)

        cache_refs = self.system.cache._get_pickable_items()
        self.assertEqual(len(cache_refs), 2)

        partial_cache = self.system.cache.partial_cache(cache_refs)
        self.assertEqual(len(partial_cache), 2)

        ## pickle, and then unpickle, after which should have lost one item
        self.system.cache.pickle("systems.tests.tempcachefile.pck")
        self.system.cache.unpickle(
            "systems.tests.tempcachefile.pck", clearcache=True)
        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(len(cache_refs), 2)

    def test_protection_and_deletion_across(self):

        ## one protected, one unprotected
        ans = self.system.test_stage1.single_instrument_no_keywords("code")
        ans2 = self.system.test_stage1.single_instrument_protected("code")

        ## one protected, one unprotected, for all markets
        ans3 = self.system.test_stage1.across_markets_no_keywords()
        ans4 = self.system.test_stage1.across_markets_protected()

        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(len(cache_refs),
                         5)  # includes base system get_instruments

        self.system.cache.delete_items_across_system()
        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(
            len(cache_refs),
            3)  # unprotected in stage, and across base_system, have gone

        cache_refs = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(len(cache_refs), 1)  # protected across system
        cache_ref = cache_refs[0]
        self.assertEqual(cache_ref.itemname,
                         "across_markets_protected")  # make sure right one

        self.system.cache.delete_items_across_system(delete_protected=True)
        cache_refs = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(len(cache_refs), 0)  # should all be gone now

    def test_protection_and_deletion_for_code(self):
        ## one protected, one unprotected
        ans = self.system.test_stage1.single_instrument_no_keywords("code")
        ans2 = self.system.test_stage1.single_instrument_protected("code")
        ans3 = self.system.test_stage1.single_instrument_no_keywords(
            "another_code")
        ans4 = self.system.test_stage1.single_instrument_protected(
            "another_code")

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 4)

        cache_refs = self.system.cache.cache_ref_list_with_protected_removed(
            cache_refs)
        self.assertEqual(len(cache_refs), 2)

        self.system.cache.delete_items_for_instrument("code")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs),
                         3)  # unprotected 'code' in stage is gone

        self.system.cache.delete_items_for_stage("test_stage1")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs),
                         2)  # unprotected 'another_code' in stage is gone

        self.system.cache.delete_items_for_instrument(
            "code", delete_protected=True)
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs),
                         1)  # just one left 'another code' protected
        cache_ref = cache_refs[0]
        self.assertEqual(cache_ref.itemname,
                         "single_instrument_protected")  # make sure right one
        self.assertEqual(cache_ref.instrument_code,
                         "another_code")  # make sure right one

        # now delete everything
        self.system.cache.delete_all_items(delete_protected=True)

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 0)  #all gone

    def test_across_stages(self):
        self.system.test_stage1.single_instrument_no_keywords("code")
        self.system.test_stage1.single_instrument_no_keywords("another_code")
        self.system.test_stage1.single_instrument_with_keywords(
            "another_code", "a_rule")
        self.system.test_stage2.single2_instrument_no_keywords("code")
        self.system.test_stage2.single_instrument_with_keywords(
            "another_code", "a_rule")

        cache_refs = self.system.cache.get_cache_refs_for_instrument("code")
        self.assertEqual(len(cache_refs), 2)

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 3)

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        itemnames = self.system.cache.get_itemnames_for_stage("test_stage2")
        itemnames.sort()
        self.assertEqual(itemnames, [
            'single2_instrument_no_keywords', 'single_instrument_with_keywords'
        ])

        self.system.cache.delete_items_for_stage("test_stage2")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage2")
        self.assertEqual(len(cache_refs), 0)
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(len(cache_refs), 3)
        cache_refs = self.system.cache.get_cache_refs_for_instrument("code")
        self.assertEqual(len(cache_refs), 1)

    def test_filtering(self):
        self.system.test_stage1.single_instrument_no_keywords("code")
        self.system.test_stage1.single_instrument_no_keywords("another_code")
        self.system.test_stage1.single_instrument_with_keywords(
            "another_code", "a_rule")
        self.system.test_stage2.single2_instrument_no_keywords("code")
        self.system.test_stage2.single_instrument_with_keywords(
            "another_code", "a_rule")

        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(len(cache_refs.filter_by_instrument_code("code")), 2)
        self.assertEqual(
            len(
                cache_refs.filter_by_itemname(
                    "single_instrument_with_keywords")), 2)
        self.assertEqual(
            len(cache_refs.filter_by_stage_name("test_stage1")), 3)
        codes = cache_refs.unique_list_of_instrument_codes()
        codes.sort()
        self.assertEqual(codes, ["All_instruments", "another_code", "code"])

        items = cache_refs.unique_list_of_item_names()
        items.sort()
        self.assertEqual(items, [
            "get_instrument_list", "single2_instrument_no_keywords",
            "single_instrument_no_keywords", "single_instrument_with_keywords"
        ])

        stage_names = cache_refs.unique_list_of_stage_names()
        stage_names.sort()
        self.assertEqual(stage_names,
                         ["base_system", "test_stage1", "test_stage2"])


if __name__ == '__main__':
    unittest.main()
