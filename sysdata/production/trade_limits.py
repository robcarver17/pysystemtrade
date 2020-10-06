"""
We want to limit the number of trades we expect to do in a given period (usually a day, but could be longer if
  eg going on holiday)

Limits per contract don't make sense, but it makes sense to limit (a) the number of times a given instrument
   within a strategy can be traded and (b) the number of times an instrument can be traded, period.
"""
import datetime
from syscore.algos import sign
from syscore.objects import arg_not_supplied, missing_data
from syslogdiag.log import logtoscreen


class tradeLimit(object):
    def __init__(
        self,
        trade_limit,
        strategy_name="",
        instrument_code="",
        period_days=1,
        trades_since_last_reset=0,
        last_reset_time=arg_not_supplied,
    ):

        self._trade_limit = int(trade_limit)
        self._period_days = period_days
        self._timedelta = datetime.timedelta(days=period_days)
        self._trades_since_last_reset = trades_since_last_reset
        self._instrument_code = instrument_code
        self._strategy_name = strategy_name

        if last_reset_time is arg_not_supplied:
            last_reset_time = datetime.datetime.now()
        self._last_reset_time = last_reset_time

    def __repr__(self):
        return (
            "Trade limit for %s %s of %d over %d days, %d trades since last reset %s" %
            (self.strategy_name,
             self.instrument_code,
             self._trade_limit,
             self.period_days,
             self.trades_since_last_reset,
             str(
                 self._last_reset_time),
             ))

    def as_dict(self):
        result_dict = dict(
            trade_limit=self.trade_limit,
            period_days=self.period_days,
            trades_since_last_reset=self.trades_since_last_reset,
            last_reset_time=self._last_reset_time,
            strategy_name=self.strategy_name,
            instrument_code=self.instrument_code,
        )

        return result_dict

    @classmethod
    def from_dict(tradeLimit, trade_limit_dict):
        return tradeLimit(**trade_limit_dict)

    def what_abs_trade_is_possible(self, abs_proposed_trade):
        # Returns proposed_trade, or a fraction thereof
        # Sign is NOT preserved

        spare_capacity = self.trade_capacity_remaining
        if abs_proposed_trade <= spare_capacity:
            abs_possible_trade = abs_proposed_trade
        else:
            abs_possible_trade = spare_capacity

        return abs_possible_trade

    @property
    def strategy_name(self):
        return self._strategy_name

    @property
    def instrument_code(self):
        return self._instrument_code

    @property
    def trade_capacity_remaining(self):
        trades_since_last_reset = self.trades_since_last_reset
        limit = self.trade_limit
        spare_capacity = limit - trades_since_last_reset

        return spare_capacity

    @property
    def trade_limit(self):
        return self._trade_limit

    @property
    def period_days(self):
        return self._period_days

    def update_limit(self, new_limit):
        assert new_limit >= 0
        self._trade_limit = int(new_limit)

    @property
    def trades_since_last_reset(self):
        self._reset_if_reset_due()

        return self._trades_since_last_reset

    @property
    def time_since_last_reset(self):
        now_time = datetime.datetime.now()
        last_reset = self._last_reset_time
        diff = now_time - last_reset

        return diff

    def _reset_if_reset_due(self):
        if self._is_reset_due():
            self.reset()

    def _is_reset_due(self):
        reset_period = self._timedelta
        diff = self.time_since_last_reset
        if diff > reset_period:
            return True
        else:
            return False

    def add_trade(self, trade_to_add):
        abs_trade_to_add = int(abs(trade_to_add))
        self._trades_since_last_reset = self._trades_since_last_reset + abs_trade_to_add

    def remove_trade(self, trade_to_remove):
        abs_trade_to_remove = int(abs(trade_to_remove))
        self._trades_since_last_reset = max(
            self._trades_since_last_reset - abs_trade_to_remove, 0
        )

    def reset(self):
        self._trades_since_last_reset = 0
        self._last_reset_time = datetime.datetime.now()


class listOfTradeLimits(list):
    def what_trade_is_possible(self, proposed_trade):
        abs_proposed_trade = abs(proposed_trade)
        possible_abs_trade = self.what_abs_trade_is_possible(
            abs_proposed_trade)
        # convert to same sign as proposed
        possible_trade = possible_abs_trade * sign(proposed_trade)

        return possible_trade

    def what_abs_trade_is_possible(self, abs_proposed_trade):
        # returns a list of abs_possible_trades
        list_of_abs_possible_trades = [
            trade_limit.what_abs_trade_is_possible(abs_proposed_trade)
            for trade_limit in self
        ]
        if len(list_of_abs_possible_trades) == 0:
            return abs_proposed_trade

        # get the smallest
        possible_abs_trade = min(list_of_abs_possible_trades)

        return possible_abs_trade

    def add_trade(self, trade_to_add):
        result = [trade_limit.add_trade(trade_to_add) for trade_limit in self]

    def remove_trade(self, trade_to_remove):
        result = [trade_limit.remove_trade(
            trade_to_remove) for trade_limit in self]

    def reset_all(self):
        result = [trade_limit.reset() for trade_limit in self]


class tradeLimitData(object):
    def __init__(self, log=logtoscreen("Overrides")):
        self.log = log
        self._limits = {}

    def default_object(self, strategy_name, instrument_code, period_days):
        return tradeLimit(
            999999,
            strategy_name=strategy_name,
            instrument_code=instrument_code,
            period_days=period_days,
        )

    def what_trade_is_possible(
            self,
            strategy_name,
            instrument_code,
            proposed_trade):
        combined_list = self._get_list_of_all_relevant_trade_limits(
            strategy_name, instrument_code
        )
        possible_trade = combined_list.what_trade_is_possible(proposed_trade)

        return possible_trade

    def add_trade(self, strategy_name, instrument_code, trade):
        combined_list = self._get_list_of_all_relevant_trade_limits(
            strategy_name, instrument_code
        )
        combined_list.add_trade(trade)
        self._update_list_of_trade_limits(combined_list)

    def remove_trade(self, strategy_name, instrument_code, trade):
        combined_list = self._get_list_of_all_relevant_trade_limits(
            strategy_name, instrument_code
        )
        combined_list.remove_trade(trade)
        self._update_list_of_trade_limits(combined_list)

    def _get_list_of_all_relevant_trade_limits(
            self, strategy_name, instrument_code):
        list_of_instrument_trade_limits = self.get_list_of_trade_limits_for_instrument(
            instrument_code)
        list_of_strategy_instrument_trade_limits = (
            self.get_list_of_trade_limits_for_strategy_instrument(
                strategy_name, instrument_code
            )
        )

        combined_list = listOfTradeLimits(
            list_of_instrument_trade_limits +
            list_of_strategy_instrument_trade_limits)

        return combined_list

    def get_list_of_trade_limits_for_instrument(self, instrument_code):
        return self.get_list_of_trade_limits_for_strategy_instrument(
            "", instrument_code
        )

    def get_list_of_trade_limits_for_strategy_instrument(
        self, strategy_name, instrument_code
    ):
        all_keys = self._get_all_limit_keys()
        trade_limits = [
            self._get_trade_limit_object(key[0], key[1], key[2])
            for key in all_keys
            if key[0] == strategy_name and key[1] == instrument_code
        ]
        list_of_trade_limits = listOfTradeLimits(trade_limits)

        return list_of_trade_limits

    def _update_list_of_trade_limits(self, list_of_trade_limits):
        result = [
            self._update_trade_limit_object(trade_limit_object)
            for trade_limit_object in list_of_trade_limits
        ]

        return result

    def update_instrument_limit_with_new_limit(
        self, instrument_code, period_days, new_limit
    ):
        self.update_instrument_strategy_limit_with_new_limit(
            "", instrument_code, period_days, new_limit
        )

    def update_instrument_strategy_limit_with_new_limit(
        self, strategy_name, instrument_code, period_days, new_limit
    ):
        trade_limit = self._get_trade_limit_object(
            strategy_name, instrument_code, period_days
        )
        trade_limit.update_limit(new_limit)
        self._update_trade_limit_object(trade_limit)

    def reset_instrument_limit(self, instrument_code, period_days):
        self.reset_instrument_strategy_limit("", instrument_code, period_days)

    def reset_instrument_strategy_limit(
        self, strategy_name, instrument_code, period_days
    ):
        trade_limit = self._get_trade_limit_object(
            strategy_name, instrument_code, period_days
        )
        trade_limit.reset()
        self._update_trade_limit_object(trade_limit)

    def get_all_limits(self):
        all_keys = self._get_all_limit_keys()
        all_limits = [
            self._get_trade_limit_object(
                key[0],
                key[1],
                key[2]) for key in all_keys]

        return all_limits

    def _get_all_limit_keys(self):
        return self._limits.keys()

    def _get_trade_limit_object(
            self,
            strategy_name,
            instrument_code,
            period_days):
        trade_limit_object = self._get_trade_limit_object_or_missing_data(
            strategy_name, instrument_code, period_days
        )
        if trade_limit_object is missing_data:
            return self.default_object(
                strategy_name, instrument_code, period_days)
        else:
            return trade_limit_object

    def _get_trade_limit_object_or_missing_data(
        self, strategy_name, instrument_code, period_days
    ):
        trade_limit_object = self._limits.get(
            (strategy_name, instrument_code, period_days), missing_data
        )
        return trade_limit_object

    def _update_trade_limit_object(self, trade_limit_object):
        strategy_name = trade_limit_object.strategy_name
        instrument_code = trade_limit_object.instrument_code
        period_days = trade_limit_object.period_days

        self._limits[(strategy_name, instrument_code,
                      period_days)] = trade_limit_object
