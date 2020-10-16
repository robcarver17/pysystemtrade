"""
We want to limit the size of position we can take, both for a given strategy and across strategies

When we want to trade (create an instrument / strategy order) we check that the new net position
  for that instrument (for the strategy, and across all strategies) doesn't exceed any limits


"""

from syscore.genutils import sign
from syscore.objects import _named_object, missing_data
from syslogdiag.log import logtoscreen

class genericForLimit(object):
    def __init__(self, name):
        self._name = name

    @property
    def key(self):
        return self._name

    @classmethod
    def from_key(genericForLimit, key):
        return genericForLimit(key)

class instrumentForLimit(object):
    def __init__(self, instrument_code):
        self._instrument_code = instrument_code

    @property
    def instrument_code(self):
        return self._instrument_code

    @property
    def key(self):
        return self.instrument_code


class instrumentStrategyForLimit(object):
    def __init__(self, strategy_name: str, instrument_code: str):
        self._instrument_code = instrument_code
        self._strategy_name = strategy_name

    @property
    def instrument_code(self):
        return self._instrument_code

    @property
    def strategy_name(self):
        return self._strategy_name

    @property
    def key(self):
        return "%s/%s" % (self.strategy_name, self.instrument_code)


NO_LIMIT = _named_object("no limit")

class positionLimit(object):
    def __init__(self, tradeable_object, position_limit: int):
        self._tradeable_object = tradeable_object
        self._position_limit = position_limit

    def __repr__(self):
        return "Position limit for %s is %s" % (str(self.key), str(self.position_limit))

    @property
    def position_limit(self):
        return self._position_limit

    @property
    def key(self):
        return self._tradeable_object.key


class positionLimitForInstrument(positionLimit):
    def __init__(self, instrument_code: str, position_limit: int):
        tradeable_object = instrumentForLimit(instrument_code)
        super().__init__(tradeable_object, position_limit)

    @classmethod
    def no_limit(positionLimitForInstrument, instrument_code):
        return positionLimitForInstrument(instrument_code, NO_LIMIT)


class positionLimitForStrategyInstrument(positionLimit):
    def __init__(self, strategy_name: str, instrument_code: str, position_limit: int):
        tradeable_object = instrumentStrategyForLimit(strategy_name, instrument_code)
        super().__init__(tradeable_object, position_limit)

    @classmethod
    def no_limit(positionLimitForStrategyInstrument, strategy_name, instrument_code):
        return positionLimitForStrategyInstrument(strategy_name, instrument_code, NO_LIMIT)


class positionLimitAndPosition(object):
    def __init__(self, position_limit_object: positionLimit, position: int):
        self._position_limit_object = position_limit_object
        self._position = position

    def __repr__(self):
        return "Position limit for %s is %s with current position %d" % (str(self.key), str(self.position_limit), self.position)

    @property
    def position(self):
        return self._position

    @property
    def position_limit(self):
        return self._position_limit_object.position_limit

    @property
    def key(self):
        return self._position_limit_object.key

    def what_trade_is_possible(self, trade:int) -> int:
        if self.position_limit is NO_LIMIT:
            return trade

        position = self.position
        new_position = position + trade

        # position limit should be abs, but just in case...
        abs_position_limit = abs(self.position_limit)
        signed_position_limit = int(abs_position_limit * sign(new_position))

        if abs(new_position)<=abs_position_limit:
            possible_trade = trade

        elif trade>0 and new_position>=0:
            possible_trade = max(0, signed_position_limit - position)

        elif trade<0 and new_position<0:
            possible_trade = min(0, signed_position_limit - position)
        else:
            possible_trade = 0

        return int(possible_trade)


class positionLimitData(object):
    def __init__(self, log=logtoscreen("Overrides")):
        self.log = log
        self._limits = {}


    def get_all_instruments_with_limits(self) -> list:
        raise NotImplementedError

    def get_all_strategy_instruments_with_limits(self)-> list:
        raise NotImplementedError

    def get_position_limit_object_for_strategy_instrument(self,
                                                       strategy_name:
                                                       str, instrument_code: str) ->positionLimitForStrategyInstrument:

        position_limit = self._get_abs_position_limit_for_strategy_instrument(strategy_name, instrument_code)
        if position_limit is missing_data:
            position_limit_object = positionLimitForStrategyInstrument.no_limit(strategy_name, instrument_code)
        else:
            position_limit_object = positionLimitForStrategyInstrument(strategy_name, instrument_code, position_limit)

        return position_limit_object

    def _get_abs_position_limit_for_strategy_instrument(self,
                                                       strategy_name:
                                                       str, instrument_code: str) ->int:
        # return missing_data if no limit found

        raise NotImplementedError

    def get_position_limit_object_for_instrument(self,
                                                              instrument_code: str) -> positionLimitForInstrument:

        position_limit = self._get_abs_position_limit_for_instrument(instrument_code)
        if position_limit is missing_data:
            position_limit_object = positionLimitForInstrument.no_limit(instrument_code)
        else:
            position_limit_object = positionLimitForInstrument(instrument_code, position_limit)

        return position_limit_object


    def _get_abs_position_limit_for_instrument(self,
                                              instrument_code: str,
                                              ) -> int:
        # return missing_data if no limit found

        raise NotImplementedError

    def set_position_limit_for_strategy_instrument(self, strategy_name:str,
                                                       instrument_code: str,
                                                       new_position_limit: int):
        raise NotImplementedError

    def set_position_limit_for_instrument(self, instrument_code: str,
                                              new_position_limit: int):
        raise NotImplementedError

    def delete_abs_position_limit_for_strategy_instrument(self, strategy_name:str,
                                                       instrument_code: str):
        raise NotImplementedError

    def delete_position_limit_for_instrument(self, instrument_code: str):

        raise NotImplementedError

