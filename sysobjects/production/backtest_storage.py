import matplotlib.pyplot as pyplot

import pandas as pd

from syscore.exceptions import missingData
from syscore.fileutils import full_filename_for_file_in_home_dir
from syscore.constants import user_exit
from syscore.interactive.menus import print_menu_of_values_and_get_response
from syscore.interactive.run_functions import (
    interactively_input_arguments_for_function,
)


class interactiveBacktest(object):
    # store backtests and interact with them
    def __init__(self, system, timestamp: str, strategy_name: str):
        self._system = system
        self._timestamp = timestamp
        self._strategy_name = strategy_name

    def __repr__(self):
        return "Backtest %s/%s" % (self.strategy_name, self.timestamp)

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def strategy_name(self):
        return self._strategy_name

    @property
    def system(self):
        return self._system

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
            try:
                result = self.interactively_get_data_and_plot_for_stage_and_method()
            except missingData:
                continue

            if result is user_exit:
                doing_stuff = False
                break

        return None

    def html_data_loop(self):
        doing_stuff = True
        while doing_stuff:
            try:
                result = self.interactively_get_data_and_html_for_stage_and_method()
            except missingData:
                continue

            if result is user_exit:
                doing_stuff = False
                break

        return None

    def print_data_loop(self):
        doing_stuff = True
        while doing_stuff:
            try:
                result = self.interactively_get_data_and_print_for_stage_and_method()
            except missingData:
                continue

            if result is user_exit:
                doing_stuff = False
                break

        return None

    def interactively_get_data_and_plot_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit:
            return data
        data.plot()
        pyplot.show()

        return None

    def interactively_get_data_and_print_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit:
            return data
        pd.set_option("display.max_rows", 10000)
        pd.set_option("display.max_columns", 50)
        pd.set_option("display.width", 1000)
        print(data)

        return None

    def interactively_get_data_and_html_for_stage_and_method(self):
        data = self.interactively_get_data_for_stage_and_method()
        if data is user_exit:
            return data
        filename = full_filename_for_file_in_home_dir("temp.html")
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
        args, kwargs = interactively_input_arguments_for_function(func, method_name)
        try:
            ans = func(*args, **kwargs)
        except Exception as e:
            print("Error %s" % e)
            raise missingData

        return ans

    def get_method_for_stage(self, stage_name, method_name):
        stage = self.get_stage(stage_name)
        func = getattr(stage, method_name)

        return func

    def get_instrument_list(self):
        return self.system.get_instrument_list()

    def get_trading_rules(self):
        return self.system.rules.trading_rules().keys()
