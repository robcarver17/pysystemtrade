import matplotlib
import matplotlib.pyplot as pyplot

# Uncomment this line if working inside IDE
# matplotlib.use("TkAgg")

import pandas as pd

from syscore.fileutils import file_in_home_dir
from syscore.objects import arg_not_supplied, user_exit, missing_data
from syscore.genutils import print_menu_of_values_and_get_response
from sysproduction.data.get_data import dataBlob
from sysproduction.diagnostic.backtest_state import (
    create_system_with_saved_state,
    get_list_of_timestamps_for_strategy,
)
from sysproduction.data.strategies import get_valid_strategy_name_from_user
from sysproduction.functions import fill_args_and_run_func


class dataBacktest(object):
    # store backtests
    def __init__(self, data=arg_not_supplied):
        # Check data has the right elements to do this
        if data is arg_not_supplied:
            data = dataBlob()
        self.data = data

    def __repr__(self):
        return "%s/%s" % (self.strategy_name, self.timestamp)

    @property
    def timestamp(self):
        timestamp = getattr(self, "_timestamp", "")
        return timestamp

    @property
    def strategy_name(self):
        strategy_name = getattr(self, "_strategy_name", "No system loaded")
        return strategy_name

    @property
    def system(self):
        current_system = getattr(self, "_system", None)
        if current_system is None:
            current_system = self.user_choose_system_with_saved_state()

        return current_system

    def user_choose_system_with_saved_state(self):
        strategy_name, timestamp = self.interactively_choose_timestamp_and_strategy()

        system = self.load_backtest(strategy_name, timestamp)
        return system

    def load_most_recent_backtest(self, strategy_name):
        list_of_timestamps = sorted(
            self.get_list_of_timestamps_for_strategy(strategy_name))
        # most recent last
        timestamp_to_use = list_of_timestamps[-1]

        system = self.load_backtest(strategy_name, timestamp_to_use)
        return system

    def load_backtest(self, strategy_name, timestamp):
        system = create_system_with_saved_state(
            self.data, strategy_name, timestamp)
        self._system = system
        self._timestamp = timestamp
        self._strategy_name = strategy_name

        return system

    def create_system_with_saved_state(self, strategy_name, timestamp):
        create_system_with_saved_state(self.data, strategy_name, timestamp)

    def interactively_choose_timestamp_and_strategy(self):
        strategy_name = get_valid_strategy_name_from_user(data=self.data)
        timestamp = self.interactively_choose_timestamp(strategy_name)

        return strategy_name, timestamp

    def interactively_choose_timestamp(self, strategy_name):
        list_of_timestamps = sorted(
            self.get_list_of_timestamps_for_strategy(strategy_name))
        # most recent last
        print("Choose the backtest to load:\n")
        timestamp = print_menu_of_values_and_get_response(
            list_of_timestamps, default_str=list_of_timestamps[-1]
        )
        return timestamp

    def get_list_of_timestamps_for_strategy(self, strategy_name):
        timestamp_list = get_list_of_timestamps_for_strategy(strategy_name)
        return timestamp_list

    def print_config_dict(self):
        system = self.system
        print(system.config.as_dict())

    def eval_loop(self):
        # allows you to interrogate any object
        system = self.system

        doing_stuff = True
        while doing_stuff:
            cmd = input(
                "Type any python command (system object is 'system'), <return> to exit> "
            )
            if cmd == "":
                doing_stuff = False
                break
            try:
                eval(cmd)
            except Exception as e:
                print("Error %s" % str(e))

        return None

    def plot_data_loop(self):
        doing_stuff = True
        while doing_stuff:
            result = self.interactively_get_data_and_plot_for_stage_and_method()
            if result is user_exit:
                doing_stuff = False
                break

        return None

    def html_data_loop(self):
        doing_stuff = True
        while doing_stuff:
            result = self.interactively_get_data_and_html_for_stage_and_method()
            if result is user_exit:
                doing_stuff = False
                break

        return None

    def print_data_loop(self):
        doing_stuff = True
        while doing_stuff:
            result = self.interactively_get_data_and_print_for_stage_and_method()
            if result is user_exit:
                doing_stuff = False
                break

        return None

    def interactively_get_data_and_plot_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit or data is missing_data:
            return data
        data.plot()
        pyplot.show()

        return None

    def interactively_get_data_and_print_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit or data is missing_data:
            return data
        pd.set_option("display.max_rows", 10000)
        pd.set_option("display.max_columns", 50)
        pd.set_option("display.width", 1000)
        print(data)

        return None

    def interactively_get_data_and_html_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit or data is missing_data:
            return data
        filename = file_in_home_dir("temp.html")
        try:
            data_as_pd = pd.DataFrame(data)
            data_as_pd.to_html(filename)
            print("Output to %s" % filename)
        except BaseException:
            print("Can't cast output %s to dataframe" % str(data))

        return None

    def interactively_get_data_for_stage_and_method(self):
        stage_name = self.interactively_choose_stage()
        if stage_name is user_exit:
            return user_exit

        method_name = self.interactively_choose_method(stage_name)
        self.print_information()
        data = self.get_result_of_method_for_stage(stage_name, method_name)

        return data

    def interactively_choose_stage(self):
        list_of_stages = self.get_list_of_stages()
        print("Which stage to acccess:\n")
        stage_name = print_menu_of_values_and_get_response(
            list_of_stages, default_str="EXIT"
        )
        if stage_name == "EXIT":
            return user_exit

        return stage_name

    def interactively_choose_method(self, stage_name):
        list_of_methods = self.get_list_of_methods_for_stage(stage_name)
        print("Which method:\n")
        method_name = print_menu_of_values_and_get_response(list_of_methods)

        return method_name

    def print_information(self):
        print(
            "Instruments: %s\nRules: %s"
            % (self.get_instrument_list(), self.get_trading_rules())
        )

    def get_list_of_stages(self):
        return self.system.stage_names

    def get_stage(self, stage_name):

        return getattr(self.system, stage_name)

    def get_list_of_methods_for_stage(self, stage_name):
        stage = self.get_stage(stage_name)
        return stage.methods()

    def get_result_of_method_for_stage(self, stage_name, method_name):
        func = self.get_method_for_stage(stage_name, method_name)
        args, kwargs = fill_args_and_run_func(func, method_name)
        try:
            ans = func(*args, **kwargs)
        except Exception as e:
            print("Error %s" % e)
            ans = missing_data

        return ans

    def get_method_for_stage(self, stage_name, method_name):
        stage = self.get_stage(stage_name)
        func = getattr(stage, method_name)

        return func

    def get_instrument_list(self):
        return self.system.get_instrument_list()

    def get_trading_rules(self):
        return self.system.rules.trading_rules().keys()
