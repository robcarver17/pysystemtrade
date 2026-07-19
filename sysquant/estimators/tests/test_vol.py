import unittest

import numpy as np
import pandas as pd

from sysquant.estimators.vol import (
    apply_price_history_eligibility,
    mixed_vol_calc,
)


class TestPriceHistoryEligibility(unittest.TestCase):
    def setUp(self):
        self.index = pd.bdate_range("2024-01-01", periods=12)
        self.vol = pd.Series(2.0, index=self.index)

    def test_controls_are_disabled_by_default(self):
        returns = pd.Series(0.0, index=self.index)

        actual = apply_price_history_eligibility(self.vol, returns)

        self.assertIs(actual, self.vol)

    def test_minimum_nonzero_changes_masks_early_history(self):
        returns = pd.Series(
            [np.nan, 0.0, 1.0, 0.0, -1.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            index=self.index,
        )

        actual = apply_price_history_eligibility(
            self.vol, returns, min_nonzero_price_changes=3
        )

        self.assertTrue(actual.iloc[:6].isna().all())
        self.assertTrue(actual.iloc[6:].eq(2.0).all())

    def test_unchanged_streak_masks_until_prices_move_again(self):
        returns = pd.Series(
            [1.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0],
            index=self.index,
        )

        actual = apply_price_history_eligibility(
            self.vol, returns, max_consecutive_unchanged_days=2
        )

        self.assertTrue(np.isnan(actual.iloc[3]))
        self.assertEqual(actual.iloc[4], 2.0)
        self.assertTrue(actual.iloc[7:9].isna().all())
        self.assertEqual(actual.iloc[9], 2.0)

    def test_invalid_limits_raise(self):
        returns = pd.Series(0.0, index=self.index)

        with self.assertRaises(ValueError):
            apply_price_history_eligibility(
                self.vol, returns, min_nonzero_price_changes=-1
            )
        with self.assertRaises(ValueError):
            apply_price_history_eligibility(
                self.vol, returns, max_consecutive_unchanged_days=-1
            )

    def test_mixed_vol_backfill_does_not_bypass_minimum_changes(self):
        index = pd.bdate_range("2024-01-01", periods=40)
        returns = pd.Series(
            [0.0] * 12 + [1.0, -1.0, 2.0] + [0.5, -0.5] * 12 + [0.25],
            index=index,
        )

        actual = mixed_vol_calc(
            returns,
            min_periods=2,
            backfill=True,
            min_nonzero_price_changes=3,
        )

        self.assertTrue(actual.iloc[:14].isna().all())
        self.assertTrue(np.isfinite(actual.iloc[14:]).all())


if __name__ == "__main__":
    unittest.main()
