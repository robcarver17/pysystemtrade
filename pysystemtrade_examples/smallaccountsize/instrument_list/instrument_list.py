'''
Created on 4 Mar 2016

@author: rob
'''

from systems.provided.futures_chapter15.estimatedsystem import PortfoliosEstimated
from systems.provided.futures_chapter15.basesystem import *
from syscore.correlations import get_avg_corr
from copy import copy
import numpy as np

config = Config("examples.smallaccountsize.smallaccount.yaml")

system = System([
    Account(), PortfoliosEstimated(), PositionSizing(), FuturesRawData(),
    ForecastCombineFixed(), ForecastScaleCapFixed(), Rules()
], csvFuturesData(), config)

system.set_logging_level("on")

assetclasses = system.data.get_instrument_asset_classes()
all_assets = list(set(assetclasses.values))

# corrmat=system.portfolio.get_instrument_correlation_matrix().corr_list[-1]
instruments = system.get_instrument_list()
max_positions = dict([(instrument_code, 2 * float(
    system.positionSize.get_volatility_scalar(instrument_code)[-250:].mean()))
                      for instrument_code in instruments])


def instr_asset_class(instrument_code, assetclasses):
    return str(assetclasses[instrument_code])


def asset_class_count(portfolio, all_assets, assetclasess):
    # for a particular, return how many of each asset class
    assets_in_portfolio = [
        instr_asset_class(code, assetclasses) for code in portfolio
    ]
    ans = dict([(asset_class, assets_in_portfolio.count(asset_class))
                for asset_class in all_assets])

    return ans


def which_asset_classes_next(my_portfolio, suitable_instruments, all_assets,
                             assetclasses):
    # returns a list of asset classes we wish to stock up on
    # will be those for which my_portfolio is short and suitable_instruments
    # have to spare
    if len(my_portfolio) == 0:
        return all_assets

    assets_in_my_portfolio = asset_class_count(my_portfolio, all_assets,
                                               assetclasses)
    suitable_assets = asset_class_count(suitable_instruments, all_assets,
                                        assetclasses)

    available = [
        asset_class for asset_class in all_assets
        if suitable_assets[asset_class] > 0
    ]

    largest_asset_class_size_in_portfolio = max(
        [assets_in_my_portfolio[asset_class] for asset_class in available])

    if all([
            assets_in_my_portfolio[asset_class] ==
            largest_asset_class_size_in_portfolio for asset_class in available
    ]):
        return available

    underweight = [
        asset_class for asset_class in all_assets
        if assets_in_my_portfolio[asset_class] <
        largest_asset_class_size_in_portfolio and
        suitable_assets[asset_class] > 0
    ]

    return underweight


def rank_within_asset_class(asset_class, suitable_instruments, assetclasses,
                            max_positions):
    # returns the largest of a list of instrument codes, ordered by maximum
    # position size
    instruments_to_check = [
        code for code in suitable_instruments
        if instr_asset_class(code, assetclasses) == asset_class
    ]

    instrument_max_positions = [
        max_positions[code] for code in instruments_to_check
    ]

    order = np.array(instrument_max_positions).argsort()

    highest_max_idx = order[-1]

    return instruments_to_check[highest_max_idx]


def choose_best_instrument(suitable_asset_classes, suitable_instruments,
                           assetclasses, max_positions):
    # select the instrument with the best max position across asset classes
    best_max_by_class = [
        rank_within_asset_class(asset_class, suitable_instruments,
                                assetclasses, max_positions)
        for asset_class in suitable_asset_classes
    ]

    instrument_max_positions = [
        max_positions[code] for code in best_max_by_class
    ]
    order = np.array(instrument_max_positions).argsort()
    highest_max_idx = order[-1]

    return best_max_by_class[highest_max_idx]


def average_correlation(instrument_code,
                        corrmat,
                        max_positions,
                        instruments,
                        portfolio=[]):
    # returns the avg correlation of instrument_code with portfolio

    if len(portfolio) == 0:
        # compare to everything
        portfolio = copy(instruments)
        portfolio.pop(portfolio.index(instrument_code))

    portfolio_index = [portfolio.index(code) for code in portfolio]
    sub_corrmat = corrmat[:, [portfolio_index]][instruments.index(
        instrument_code), :]
    avg_corr = np.mean(sub_corrmat)

    return avg_corr


def return_lowest_five(avg_correlation_list, suitable_instruments):
    """
    Returns names of instruments with lowest 5 correlations
    """

    order = np.array(avg_correlation_list).argsort()
    top_five = order[:5]
    shortlist = [suitable_instruments[xidx] for xidx in top_five]

    return shortlist


def return_highest_max_position(shortlist, max_positions):

    maxpos_shortlist = [max_positions[code] for code in shortlist]
    order = np.array(maxpos_shortlist).argsort()
    return shortlist[order[-1]]


my_portfolio = []

suitable_instruments = copy(instruments)
suitable_instruments.pop(suitable_instruments.index("SHATZ"))

while len(suitable_instruments) > 0:
    suitable_asset_classes = which_asset_classes_next(
        my_portfolio, suitable_instruments, all_assets, assetclasses)
    best = choose_best_instrument(suitable_asset_classes, suitable_instruments,
                                  assetclasses, max_positions)
    print('{0: <12} '.format(best), max_positions[best])

    my_portfolio.append(best)
    suitable_instruments.pop(suitable_instruments.index(best))
