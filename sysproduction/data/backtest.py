## 3 things going on here
## a data class
## an interactive thing
## a backtest object
#
# split them up!


# Uncomment this line if working inside IDE
#
import matplotlib
matplotlib.use("TkAgg")

from syscore.objects import arg_not_supplied
from syscore.genutils import print_menu_of_values_and_get_response
from sysdata.data_blob import dataBlob
from sysobjects.production.backtest import interactiveBacktest
from sysproduction.diagnostic.backtest_state import (
    create_system_with_saved_state,
    get_list_of_timestamps_for_strategy,
)
from sysproduction.data.strategies import get_valid_strategy_name_from_user


class dataBacktest(object):
    # store backtests
    def __init__(self, data: dataBlob=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        self.data = data


    def get_most_recent_backtest(self, strategy_name: str) -> interactiveBacktest:
        list_of_timestamps = sorted(
            self.get_list_of_timestamps_for_strategy(strategy_name))
        # most recent last
        timestamp_to_use = list_of_timestamps[-1]

        backtest = self.load_backtest(strategy_name, timestamp_to_use)
        return backtest

    def load_backtest(self, strategy_name: str, timestamp: str)  -> interactiveBacktest:
        system = create_system_with_saved_state(
            self.data, strategy_name, timestamp)

        backtest = interactiveBacktest(system=system,
                                       strategy_name=strategy_name,
                                       timestamp=timestamp)

        return backtest


    def get_list_of_timestamps_for_strategy(self, strategy_name):
        timestamp_list = get_list_of_timestamps_for_strategy(strategy_name)
        return timestamp_list


def user_choose_backtest(data: dataBlob = arg_not_supplied) -> interactiveBacktest:
    strategy_name, timestamp = interactively_choose_strategy_name_timestamp_for_backtest(data)
    data_backtest = dataBacktest(data=data)
    backtest = data_backtest.load_backtest(strategy_name=strategy_name, timestamp=timestamp)

    return backtest

def interactively_choose_strategy_name_timestamp_for_backtest(data: dataBlob = arg_not_supplied) -> (str, str):
    strategy_name = get_valid_strategy_name_from_user(data=data)
    timestamp = interactively_choose_timestamp(data=data, strategy_name=strategy_name)

    return strategy_name, timestamp

def interactively_choose_timestamp(strategy_name: str, data: dataBlob = arg_not_supplied):
    data_backtest = dataBacktest(data)
    list_of_timestamps = sorted(
        data_backtest.get_list_of_timestamps_for_strategy(strategy_name))
    # most recent last
    print("Choose the backtest to load:\n")
    timestamp = print_menu_of_values_and_get_response(
        list_of_timestamps, default_str=list_of_timestamps[-1]
    )
    return timestamp


