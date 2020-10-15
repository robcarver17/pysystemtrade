"""
We want to limit the size of position we can take, both for a given strategy and across strategies

When we want to trade (create an instrument / strategy order) we check that the new net position
  for that instrument (for the strategy, and across all strategies) doesn't exceed any limits


"""
from syslogdiag.log import logtoscreen

class positionLimitData(object):
    def __init__(self, log=logtoscreen("Overrides")):
        self.log = log
        self._limits = {}

    def check_if_position_okay_for_strategy_instrument(
            self,
            strategy_name,
            instrument_code,
            proposed_position):

        limit_abs_position = self.get_abs_position_limit_for_strategy_instrument(strategy_name, instrument_code)
        proposed_abs_position = abs(proposed_position)

        position_okay = proposed_abs_position<=limit_abs_position

        return position_okay

    def check_if_position_okay_for_instrument(
            self,
            instrument_code,
            proposed_position):

        limit_abs_position = self.get_abs_position_limit_for_instrument(instrument_code)
        proposed_abs_position = abs(proposed_position)

        position_okay = proposed_abs_position<=limit_abs_position

        return position_okay


    def get_all_instrument_limits(self):
        instruments_with_limits = self.get_all_instruments_with_limits()
        all_limits = dict([(instrument_code, self.get_abs_position_limit_for_instrument(instrument_code))
                            for instrument_code in instruments_with_limits])

        return all_limits

    def get_all_strategy_instrument_limits(self):
        strategy_instruments_with_limits = self.get_all_strategy_instruments_with_limits()
        all_limits = dict([((strategy_name, instrument_code),
                            self.get_abs_position_limit_for_strategy_instrument(strategy_name, instrument_code))
                            for (strategy_name, instrument_code) in strategy_instruments_with_limits])

        return all_limits

    def get_all_instruments_with_limits(self):
        raise NotImplementedError

    def get_all_strategy_instruments_with_limits(self):
        raise NotImplementedError

    def get_abs_position_limit_for_strategy_instrument(self, strategy_name, instrument_code):
        raise NotImplementedError

    def get_abs_position_limit_for_instrument(self, instrument_code):
        raise NotImplementedError

    def set_abs_position_limit_for_strategy_instrument(self, strategy_name, instrument_code, new_position_limit):
        raise NotImplementedError

    def set_abs_position_limit_for_instrument(self, instrument_code, new_position_limit):
        raise NotImplementedError
