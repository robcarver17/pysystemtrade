import unittest

import numpy as np
import pandas as pd

from syscore.pandas.strategy_functions import calculate_cost_deflator


class TestCostDeflator(unittest.TestCase):
    def test_valid_prices_produce_finite_deflator(self):
        index = pd.bdate_range("2020-01-01", periods=300)
        daily_moves = 0.2 + np.sin(np.arange(len(index)) / 7.0)
        prices = pd.Series(100.0 + np.cumsum(daily_moves), index=index)

        deflator = calculate_cost_deflator(prices)

        self.assertEqual(deflator.iloc[-1], 1.0)
        self.assertTrue(np.isfinite(deflator.dropna()).all())

    def test_flat_terminal_window_is_rejected(self):
        index = pd.bdate_range("2020-01-01", periods=500)
        changing_prices = np.linspace(100.0, 120.0, 120)
        flat_prices = np.full(len(index) - len(changing_prices), changing_prices[-1])
        prices = pd.Series(
            np.concatenate([changing_prices, flat_prices]), index=index
        )

        with self.assertRaisesRegex(ValueError, "terminal volatility"):
            calculate_cost_deflator(prices)

    def test_insufficient_history_remains_missing(self):
        index = pd.bdate_range("2020-01-01", periods=2)
        prices = pd.Series([100.0, 101.0], index=index)

        deflator = calculate_cost_deflator(prices)

        self.assertTrue(deflator.isna().all())


if __name__ == "__main__":
    unittest.main()
