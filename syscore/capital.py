"""
Functions to calculate capital multiplier

ALl return Tx1 pd.Series
"""
from copy import copy
import pandas as pd
import numpy as np


def fixed_capital(system, **ignored_args):
    multiplier = copy(system.accounts.portfolio().percent())
    multiplier[:] = 1.0

    return multiplier


def full_compounding(system, **ignored_args):
    pandl = system.accounts.portfolio().percent()
    multiplier = 1.0 + (pandl / 100.0)
    multiplier = multiplier.cumprod().ffill()

    return multiplier


def half_compounding(system, **ignored_args):
    pandl = system.accounts.portfolio().percent().curve().ffill().diff()
    multiplier = 1.0
    multiplier_list = []
    for daily_return in pandl:
        actual_return = multiplier * daily_return / 100.0
        multiplier = multiplier * (1.0 + actual_return)
        multiplier = np.nanmin([multiplier, 1.0])
        multiplier_list.append(multiplier)

    multiplier = pd.Series(multiplier_list, index=pandl.index).ffill()

    return multiplier
