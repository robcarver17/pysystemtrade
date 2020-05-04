from syscore.objects import arg_not_supplied, failure, success, missing_data
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.production.generic_timed_storage import timedEntry, listOfEntries, listOfEntriesData


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

GLOBAL_STRATEGY = 'GLOBAL'
BROKER_ACCOUNT_VALUE = 'BROKER'
MAXIMUM_ACCOUNT_VALUE = 'MAX'

SPECIAL_NAMES = [GLOBAL_STRATEGY, BROKER_ACCOUNT_VALUE, MAXIMUM_ACCOUNT_VALUE]

class capitalData(listOfEntriesData):
    """
    Store and retrieve the capital assigned to a particular strategy

    A seperate process is required to map from account value to strategy capital

    We also store the total account value (GLOBAL STRATEGY), broker account value (BROKER_ACCOUNT_VALUE),
       and for half compounding purposes MAXIMUM_ACCOUNT_VALUE
    """
    def _name(self):
        return "capitalData"

    def _data_class_name(self):
        return "sysdata.production.capital.capitalForStrategy"

    def get_total_capital_pd_series(self):
        return self.get_capital_pd_series_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value_pd_series(self):
        return self.get_capital_pd_series_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_maximum_account_value_pd_series(self):
        return self.get_capital_pd_series_for_strategy(MAXIMUM_ACCOUNT_VALUE)

    def get_capital_pd_series_for_strategy(self, strategy_name):
        capital_series = self._get_series_for_args_dict(dict(strategy_name=strategy_name))
        pd_series = capital_series.as_pd_df()
        return pd_series

    def get_current_total_capital(self):
        return self.get_current_capital_for_strategy(GLOBAL_STRATEGY)

    def get_broker_account_value(self):
        return self.get_current_capital_for_strategy(BROKER_ACCOUNT_VALUE)

    def get_current_maximum_account_value(self):
        return self.get_current_capital_for_strategy(MAXIMUM_ACCOUNT_VALUE)

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
        for strat_name in SPECIAL_NAMES:
            try:
                strategy_names.pop(strat_name)
            except IndexError:
                ## Don't have to have capital defined
                pass

        return strategy_names

    def delete_last_capital_for_total_strategy(self,  are_you_sure=False):
        self.delete_last_capital_for_strategy(GLOBAL_STRATEGY, are_you_sure = are_you_sure)

    def delete_last_capital_for_strategy(self, strategy_name, are_you_sure=False):
        self._delete_last_entry_for_args_dict(dict(strategy_name=strategy_name), are_you_sure=are_you_sure)


LIST_OF_COMPOUND_METHODS = ['full', 'half', 'fixed']


class totalCapitalCalculationData(object):
    """
    This object allows us to calculate available total capital from previous capital and profits

    It uses the special strategy names GLOBAL_STRATEGY and BROKER_ACCOUNT_VALUE

    Three different compounding methods are available

    """

    def __init__(self, capital_data: capitalData, calc_method="compound", calc_method_args={}):
        """
        Calculation methods are: full- all profits and losses go to capital, half - profits past the HWM are not added,
           fixed - capital is unaffected by profits and losses (not reccomendded!)

        :param capital_data:
        :param calc_method: method for going from profits to capital allocated
        """
        self._capital_data = capital_data

        try:
            assert calc_method in LIST_OF_COMPOUND_METHODS
        except:
            raise Exception("Capital calculation %s has to be one of %s" % (calc_method, LIST_OF_COMPOUND_METHODS))

    def __repr__(self):
        if self._strategy_name==GLOBAL_STRATEGY:
            strat_name = "total capital"
        else:
            strat_name = self._strategy_name
        return "capitalCalculationData for %s, %s" % (self._capital_data, strat_name)

    def get_capital_pd_series(self):
        return self._capital_data.get_capital_pd_series_for_strategy(self._strategy_name)

    def get_current_capital(self):
        return self._capital_data.get_current_capital_for_strategy(self._strategy_name)

    def get_total_capital_with_new_broker_account_value(self, value):
        """
        does everything you'd expect when a new broker account value arrives:
           - add on to broker account value series
           - get p&l since last broker
            - call capital calculation function, which will update


        :param value:
        :return:
        """

        pass

    def adjust_broker_account_for_delta(self, value):
        """

        FIX ME NEED CALLER FUNCTION FOR COMMAND LINE CAPITAL ACTIVITIES
        :param value: change in account value to be ignore, a minus figure is a withdrawal, positive is deposit
        :return: None
        """
        pass

    def modify_maximum_account_value(self, value):
        """

        FIX ME NEED CALLER FUNCTION FOR COMMAND LINE CAPITAL ACTIVITIES
        :param value: new_maximum_account_value
        :return: None
        """
        pass