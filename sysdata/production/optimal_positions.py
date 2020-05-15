"""

Optimal positions describe what a particular trading strategy would like to do, conditional (or not) on prices and
  current positions

The exact implementation of this depends on the strategy.
A basic class is an optimal position with buffers around it.
A mean reversion style class would include price buffers

"""

import pandas as pd

from syscore.objects import arg_not_supplied, failure, success, missing_data
from sysdata.data import baseData
from syslogdiag.log import logtoscreen
from sysdata.production.generic_timed_storage import timedEntry, listOfEntries, listOfEntriesData


class simpleOptimalPosition(timedEntry):
    """
    This is the simplest possible optimal positions object

    """

    def _setup_args_data(self):
        self._star_args = ['position'] # compulsory args

    def _name_(self):
        return "simpleOptimalPosition"

    def _containing_data_class_name(self):
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"



class bufferedOptimalPositions(timedEntry):
    """
    Here is one with buffers

    """
    def _setup_args_data(self):
        self._star_args = ['lower_position', 'upper_position'] # compulsory args

    def _name_(self):
        return "bufferedOptimalPosition"

    def _containing_data_class_name(self):
        return "sysdata.production.optimal_positions.bufferedOptimalPositionForInstrument"


    def _kwargs_checks(self, kwargs):
        try:
            assert kwargs['upper_position']>=kwargs['lower_position']
        except:
            raise Exception("Upper position has to be higher than lower position")



class simpleOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return simpleOptimalPosition


class bufferedOptimalPositionForInstrument(listOfEntries):
    """
    A list of positions
    """

    def _entry_class(self):
        return bufferedOptimalPositions


class optimalPositionData(listOfEntriesData):
    """
    Store and retrieve the optimal positions assigned to a particular strategy

    We store the type of list in the data
    """
    def _name(self):
        return "optimalPositionData"

    def _data_class_name(self):
        ## This is the default, may be overriden
        return "sysdata.production.optimal_positions.simpleOptimalPositionForInstrument"

    def get_optimal_position_as_df_for_strategy_and_instrument(self, strategy_name, instrument_code):
        position_series = self._get_series_for_args_dict(dict(strategy_name = strategy_name,
                                                              instrument_code = instrument_code))
        df_object = position_series.as_pd_df()
        return df_object

    def get_current_optimal_position_for_strategy_and_instrument(self, strategy_name, instrument_code):
        current_optimal_position_entry = self._get_current_entry_for_args_dict(dict(strategy_name=strategy_name,
                                                                           instrument_code = instrument_code))

        return current_optimal_position_entry

    def update_optimal_position_for_strategy_and_instrument(self, strategy_name, instrument_code, position_entry):

        try:
            self._update_entry_for_args_dict(position_entry, dict(strategy_name = strategy_name,
                                                                 instrument_code = instrument_code))
        except Exception as e:
            self.log.warn(
                "Error %s when updating position for %s/%s with %s" % (str(e), strategy_name,
                                                                    instrument_code, str(position_entry)))
            return failure

    def get_list_of_strategies_and_instruments_with_optimal_position(self):
        list_of_args_dict = self._get_list_of_args_dict()
        strat_instr_tuples =[]
        for arg_entry in list_of_args_dict:
            strat_instr_tuples.append((arg_entry['strategy_name'], arg_entry['instrument_code']))

        return strat_instr_tuples

    def get_list_of_instruments_for_strategy_with_optimal_position(self, strategy_name):
        list_of_all_positions = self.get_list_of_strategies_and_instruments_with_optimal_position()
        list_of_instruments = [position[1] for position in list_of_all_positions if position[0]==strategy_name]

        return list_of_instruments

    def delete_last_position_for_strategy_and_instrument(self, strategy_name, instrument_code, are_you_sure=False):
        self._delete_last_entry_for_args_dict(dict(strategy_name=strategy_name,
                                                   instrument_code = instrument_code),
                                                are_you_sure=are_you_sure)
