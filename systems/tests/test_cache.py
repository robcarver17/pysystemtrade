import unittest

from systems.stage import SystemStage
from systems.basesystem import System
from systems.system_cache import input, diagnostic, output, ALL_KEYNAME
from sysdata.sim.sim_data import simData
from sysdata.config.configdata import Config


class testStage1(SystemStage):
    @property
    def name(self):
        return "test_stage1"

    @diagnostic()
    def single_instrument_no_keywords(self, instrument_code):
        return 5

    @diagnostic()
    def single_instrument_with_keywords(self, instrument_code, keyword):
        return 6

    @diagnostic()
    def single_instrument_with_keywords_and_flags(
        self, instrument_code, keyword, x_flag=3
    ):
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
    @property
    def name(self):
        return "test_stage2"

    @input
    def input2_stage_no_caching(self, x):
        return x

    @diagnostic()
    def single2_instrument_no_keywords(self, instrument_code):
        return 14

    @diagnostic()
    def single_instrument_with_keywords(self, instrument_code, variation_name):
        # deliberate duplicate
        return 15


@unittest.SkipTest
class TestCache(unittest.TestCase):
    def setUp(self):

        system = System(
            [testStage1(), testStage2()],
            simData(),
            Config(dict(instruments=["code", "another_code"])),
        )
        self.system = system

    def test_get_instrument_list(self):
        self.system.get_instrument_list()
        self.system.get_instrument_list()
        self.assertEqual(3, len(self.system.cache.get_items_with_data()))

    def test_stage_input_wrapper(self):
        # this shouldn't cache
        not_used = self.system.test_stage2.input2_stage_no_caching(5.0)
        # check cache still empty
        self.assertEqual(0, len(self.system.cache.get_items_with_data()))

    def test_single_instrument_no_keywords(self):

        self.system.test_stage1.single_instrument_no_keywords("code")
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual("code", cache_ref.instrument_code)
        self.assertEqual(5, self.system.cache[cache_ref].value())
        self.assertEqual(
            4, len(self.system.cache._get_pickable_items())
        )  # includes cache of instrument list
        self.assertEqual(0, len(self.system.cache._get_protected_items()))

        cache_ref_list = self.system.cache.get_items_with_data()

        # no protected, so should still have two elements inside
        self.assertEqual(
            4,
            len(
                self.system.cache.cache_ref_list_with_protected_removed(cache_ref_list)
            ),
        )

        self.system.cache.delete_all_items()

        # not protected so deletion should work
        self.assertEqual(0, len(self.system.cache.get_items_with_data()))

    def test_single_instrument_with_keywords(self):

        self.system.test_stage1.single_instrument_with_keywords("code", "keyname")
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual("code", cache_ref.instrument_code)
        self.assertEqual("keyname", cache_ref.keyname)
        self.assertEqual(6, self.system.cache[cache_ref].value())

    def test_single_instrument_with_keywords_and_flags(self):
        self.system.test_stage1.single_instrument_with_keywords_and_flags(
            "code", "keyname", x_flag=True
        )
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual("code", cache_ref.instrument_code)
        self.assertEqual("keyname", cache_ref.keyname)
        self.assertEqual((7, True), self.system.cache[cache_ref].value())
        self.assertEqual("x_flag=True", cache_ref.flags)

    def test_across_markets_no_keywords(self):
        ans = self.system.test_stage1.across_markets_no_keywords()
        cache_ref = self.system.cache.get_cacherefs_for_stage("test_stage1")[0]
        self.assertEqual(ALL_KEYNAME, cache_ref.instrument_code)
        self.assertEqual("", cache_ref.keyname)

        ans = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(4, len(ans))  # also includes base_system.get_instrument_list()

        # test deletion across ...
        self.system.test_stage1.single_instrument_no_keywords(
            "code"
        )  # this shouldn't be deleted ...
        self.system.cache.delete_items_across_system()  # ... when we do this

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(1, len(cache_refs))
        cache_ref = cache_refs[0]
        self.assertEqual("single_instrument_no_keywords", cache_ref.itemname)

        # incidentally should also wipe out this guy
        cache_refs = self.system.cache.get_cacherefs_for_stage(self.system.name)
        self.assertEqual(0, len(cache_refs))

    def test_pickling(self):
        ans = self.system.test_stage1.across_markets_no_keywords()
        ans2 = self.system.test_stage1.single_instrument_not_pickable()

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(2, len(cache_refs))

        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(5, len(cache_refs))

        cache_refs = self.system.cache._get_pickable_items()
        self.assertEqual(4, len(cache_refs))

        partial_cache = self.system.cache.partial_cache(cache_refs)
        self.assertEqual(4, len(partial_cache))

        # pickle, and then unpickle, after which should have lost one item
        self.system.cache.pickle("systems.tests.tempcachefile.pck")
        self.system.cache.unpickle("systems.tests.tempcachefile.pck", clearcache=True)
        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(4, len(cache_refs))

    def test_protection_and_deletion_across(self):

        # one protected, one unprotected
        ans = self.system.test_stage1.single_instrument_no_keywords("code")
        ans2 = self.system.test_stage1.single_instrument_protected("code")

        # one protected, one unprotected, for all markets
        ans3 = self.system.test_stage1.across_markets_no_keywords()
        ans4 = self.system.test_stage1.across_markets_protected()

        cache_refs = self.system.cache.get_items_with_data()
        # includes base system get_instruments
        self.assertEqual(7, len(cache_refs))

        self.system.cache.delete_items_across_system()
        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(
            3, len(cache_refs)
        )  # unprotected in stage, and across base_system, have gone

        cache_refs = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(1, len(cache_refs))  # protected across system
        cache_ref = cache_refs[0]
        self.assertEqual(
            "across_markets_protected", cache_ref.itemname
        )  # make sure right one

        self.system.cache.delete_items_across_system(delete_protected=True)
        cache_refs = self.system.cache.get_cache_refs_across_system()
        self.assertEqual(0, len(cache_refs))  # should all be gone now

    def test_protection_and_deletion_for_code(self):
        # one protected, one unprotected
        ans = self.system.test_stage1.single_instrument_no_keywords("code")
        ans2 = self.system.test_stage1.single_instrument_protected("code")
        ans3 = self.system.test_stage1.single_instrument_no_keywords("another_code")
        ans4 = self.system.test_stage1.single_instrument_protected("another_code")

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(4, len(cache_refs))

        cache_refs = self.system.cache.cache_ref_list_with_protected_removed(cache_refs)
        self.assertEqual(2, len(cache_refs))

        self.system.cache.delete_items_for_instrument("code")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        # unprotected 'code' in stage is gone
        self.assertEqual(3, len(cache_refs))

        self.system.cache.delete_items_for_stage("test_stage1")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(
            2, len(cache_refs)
        )  # unprotected 'another_code' in stage is gone

        self.system.cache.delete_items_for_instrument("code", delete_protected=True)
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        # just one left 'another code' protected
        self.assertEqual(1, len(cache_refs))
        cache_ref = cache_refs[0]
        self.assertEqual(
            "single_instrument_protected", cache_ref.itemname
        )  # make sure right one
        self.assertEqual(
            "another_code", cache_ref.instrument_code
        )  # make sure right one

        # now delete everything
        self.system.cache.delete_all_items(delete_protected=True)

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(0, len(cache_refs))  # all gone

    def test_across_stages(self):
        self.system.test_stage1.single_instrument_no_keywords("code")
        self.system.test_stage1.single_instrument_no_keywords("another_code")
        self.system.test_stage1.single_instrument_with_keywords(
            "another_code", "a_rule"
        )
        self.system.test_stage2.single2_instrument_no_keywords("code")
        self.system.test_stage2.single_instrument_with_keywords(
            "another_code", "a_rule"
        )

        cache_refs = self.system.cache.get_cache_refs_for_instrument("code")
        self.assertEqual(2, len(cache_refs))

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(3, len(cache_refs))

        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        itemnames = sorted(self.system.cache.get_itemnames_for_stage("test_stage2"))
        self.assertEqual(
            ["single2_instrument_no_keywords", "single_instrument_with_keywords"],
            itemnames,
        )

        self.system.cache.delete_items_for_stage("test_stage2")
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage2")
        self.assertEqual(0, len(cache_refs))
        cache_refs = self.system.cache.get_cacherefs_for_stage("test_stage1")
        self.assertEqual(3, len(cache_refs))
        cache_refs = self.system.cache.get_cache_refs_for_instrument("code")
        self.assertEqual(1, len(cache_refs))

    def test_filtering(self):
        self.system.test_stage1.single_instrument_no_keywords("code")
        self.system.test_stage1.single_instrument_no_keywords("another_code")
        self.system.test_stage1.single_instrument_with_keywords(
            "another_code", "a_rule"
        )
        self.system.test_stage2.single2_instrument_no_keywords("code")
        self.system.test_stage2.single_instrument_with_keywords(
            "another_code", "a_rule"
        )

        cache_refs = self.system.cache.get_items_with_data()
        self.assertEqual(2, len(cache_refs.filter_by_instrument_code("code")))
        self.assertEqual(
            2, len(cache_refs.filter_by_itemname("single_instrument_with_keywords"))
        )
        self.assertEqual(3, len(cache_refs.filter_by_stage_name("test_stage1")))
        codes = sorted(cache_refs.unique_list_of_instrument_codes())
        self.assertEqual(["All_instruments", "another_code", "code"], codes)

        items = cache_refs.unique_list_of_item_names()
        items.sort()
        self.assertEqual(
            [
                "get_instrument_list",
                "get_list_of_ignored_instruments_to_remove",
                "get_list_of_instruments_to_remove",
                "single2_instrument_no_keywords",
                "single_instrument_no_keywords",
                "single_instrument_with_keywords",
            ],
            items,
        )

        stage_names = cache_refs.unique_list_of_stage_names()
        stage_names.sort()
        self.assertEqual(["base_system", "test_stage1", "test_stage2"], stage_names)


if __name__ == "__main__":
    unittest.main()
