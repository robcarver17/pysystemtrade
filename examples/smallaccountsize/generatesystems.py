instrument_list = [
    'KR3', 'V2X', 'EDOLLAR', 'MXP', 'CORN', 'EUROSTX', 'GAS_US', 'PLAT', 'US2',
    'LEANHOG', 'GBP', 'VIX', 'CAC', 'COPPER', 'CRUDE_W', 'BOBL', 'WHEAT',
    'JPY', 'NASDAQ', 'GOLD', 'US5', 'SOYBEAN', 'AUD', 'SP500', 'PALLAD',
    'KR10', 'LIVECOW', 'NZD', 'KOSPI', 'US10', 'SMI', 'EUR', 'OAT', 'AEX',
    'BUND', 'BTP', 'US20'
]

instrument_sets = []
for idx in range(9)[1:]:
    instrument_sets.append(instrument_list[:idx])

for idx in [15, 20, 25, 38]:
    instrument_sets.append(instrument_list[:idx])

from systems.portfolio import PortfoliosEstimated
from systems.provided.futures_chapter15.basesystem import *
from syscore.correlations import get_avg_corr
from copy import copy
import numpy as np
from pickle import dump, load

config = Config("examples.smallaccountsize.smallaccount.yaml")

mkt_counters = []

idm = []
acc_curve = []
roll_acc = []

for (idx, instr_set) in enumerate(instrument_sets):
    config.instruments = instr_set
    system = System([
        Account(), PortfoliosEstimated(), PositionSizing(), FuturesRawData(),
        ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
    ], csvFuturesData(), config)

    system.config.instrument_div_mult_estimate['dm_max'] = 100.0
    system.set_logging_level("on")

    idm.append(system.portfolio.get_instrument_diversification_multiplier())

    acc = system.accounts.portfolio(roundpositions=False)
    acc_curve.append(acc)
    roll_acc.append(acc.weekly.rolling_ann_std(22))
    mktcount = acc.to_frame().shape[1] - np.isnan(acc.to_frame()).sum(axis=1)
    mkt_counters.append(mktcount)

import pandas as pd
roll_acc = []
mkt_counters = []
for acc in acc_curve:
    y = pd.rolling_std(
        acc.weekly.as_df(), 20, min_periods=4,
        center=True) * acc.weekly._vol_scalar

    roll_acc.append(y)

    mktcount = acc.to_frame().shape[1] - np.isnan(acc.to_frame()).sum(axis=1)
    mkt_counters.append(mktcount)

ans = [roll_acc, idm, acc_curve, mkt_counters]
with open("/home/rob/data.pck", "wb") as f:
    dump(ans, f)
