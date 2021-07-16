"""
NOTES:

Uses capital already obtained and available through data.

*Could* also get various other capital information from IB

accountValues
accountSummary
portfolio
positions

reqPnL
pnl
cancelPnL

reqPnLSingle
pnlSingle
cancelPnLSingle

    All of this is passed to a single capital allocator function that calculates how much capital each strategy should be allocated
      and works out the p&l for each strategy

    This can be done in various ways, eg by instrument, by asset class, as a % of total account value
       ... allow each strategy to keep it's p&l, or redistribute


"""

from sysproduction.data.capital import dataCapital
from sysdata.data_blob import dataBlob
from syscore.objects import missing_data, arg_not_supplied
from sysproduction.data.strategies import get_list_of_strategies_from_config

def weighted_strategy_allocation(data: dataBlob, strategy_weights: dict = arg_not_supplied):
    """
    Used to allocate capital to strategies

    To use another function; change configuration item 'strategy_capital_allocation.function'
    All other elements in that configuration are passed as *kwargs to this function

    :param data: A data blob
    :param strategy_weights: dict of float
    :return: dict of capital values per strategy
    """
    if strategy_weights is arg_not_supplied:
        strategy_weights = strategy_weights_if_none_passed(data)

    sum_of_weights = sum(strategy_weights.values())
    total_capital = get_total_current_capital(data)
    output_dict = {}
    for strategy_name, weight in strategy_weights.items():
        strategy_capital = (weight / sum_of_weights) * total_capital
        output_dict[strategy_name] = strategy_capital

    return output_dict


def get_total_current_capital(data: dataBlob) -> float:
    data_capital = dataCapital(data)
    total_capital = data_capital.get_current_total_capital()

    if total_capital is missing_data:
        data.log.critical(
            "Can't allocate strategy capital without total capital")
        raise Exception()

    return total_capital

def strategy_weights_if_none_passed(data: dataBlob) -> dict:
    list_of_strategies = get_list_of_strategies_from_config(data)
    count_of_strateges = len(list_of_strategies)
    weight = 100.0/count_of_strateges
    data.log.warn("No configuration for strategy weight defined in private config; equally weighting across %s each gets %f percent" %
             (str(list_of_strategies), weight))
    output_dict = dict([(strat_name, weight) for strat_name in list_of_strategies])

    return output_dict
