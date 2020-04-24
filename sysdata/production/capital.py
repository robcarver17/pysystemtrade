from syscore.objects import arg_not_supplied, failure, success, missing_data
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.production.generic_timed_storage import timedEntry, listOfEntries, listOfEntriesData

DEFAULT_CURRENCY = "GBP"

class capitalEntry(timedEntry):

    def _setup_args_data(self):
        self._star_args = ['capital_value'] # compulsory args

    def _name_(self):
        return "Capital"

    def _containing_data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"

    def _kwargs_checks(self, kwargs):
        try:
            assert kwargs['capital_value']>0.0
        except:
            raise Exception("Capital has to be positive")

class capitalForStrategy(listOfEntries):
    """
    A list of capitalEntry
    """

    def _entry_class(self):
        return capitalEntry


class capitalData(listOfEntriesData):
    """
    Store and retrieve the capital assigned to a particular strategy

    A seperate process is required to map from account value to strategy capital

    """
    def _name(self):
        return "capitalData"

    def _data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"

    def get_capital_pd_series_for_strategy(self, strategy_name):
        capital_series = self._get_series_for_args_dict(dict(strategy_name=strategy_name))
        pd_series = capital_series.as_pd_df()
        return pd_series

    def get_current_capital_for_strategy(self, strategy_name):
        current_capital_entry = self._get_current_entry_for_args_dict(dict(strategy_name = strategy_name))
        if current_capital_entry is missing_data:
            return missing_data

        capital_value = current_capital_entry.capital_value

        return capital_value

    def update_capital_value_for_strategy(self, strategy_name, new_capital_value):
        new_capital_entry = capitalEntry(new_capital_value)
        try:
            self._update_entry_for_args_dict(new_capital_entry, dict(strategy_name=strategy_name))
        except Exception as e:
            self.log.warn("Error %s when updating capital for %s with %s" % (str(e), strategy_name, str(new_capital_entry)))
            return failure

    def get_list_of_strategies_with_capital(self):
        list_of_args_dict = self._get_list_of_args_dict()
        strategy_names = [d['strategy_name'] for d in list_of_args_dict]
        strategy_names = list(set(strategy_names))

        return strategy_names

    def delete_last_capital_for_strategy(self, strategy_name, are_you_sure=False):
        self._delete_last_entry_for_args_dict(dict(strategy_name=strategy_name), are_you_sure=are_you_sure)
