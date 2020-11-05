"""
An override is something that affects our normal trading behaviour
"""

import numpy as np

from syscore.objects import _named_object
from syscore.genutils import sign
from syslogdiag.log import logtoscreen

override_close = _named_object("Close")
override_no_trading = _named_object("No trading")
override_reduce_only = _named_object("Reduce only")
override_none = _named_object("No override")

override_dict = {
    override_close: 0.0,
    override_none: 1.0,
    override_no_trading: -1.0,
    override_reduce_only: -2.0,
}
_override_lookup = []
for key, value in override_dict.items():
    _override_lookup.append((value, key))


def lookup_value_and_return_float_or_object(value):
    value_list = [entry[1] for entry in _override_lookup if entry[0] == value]
    if len(value_list) == 0:
        return value
    else:
        return value_list[0]


class Override:
    def __init__(self, value):
        try:
            if value in override_dict.keys():
                self._override = value
            elif isinstance(value, float) or isinstance(value, int):
                assert value >= 0.0
                assert value <= 1.0
                self._override = float(value)
            else:
                raise Exception()
        except BaseException:
            raise Exception(
                "Override must be between 0.0 and 1.0, or one of the following objects %s" %
                override_dict)

    def __repr__(self):
        return "Override %s" % str(self._override)

    def as_float(self):
        value = self._override
        if value in override_dict.keys():
            return override_dict[value]
        else:
            return value

    @classmethod
    def from_float(Override, value):
        value_or_object = lookup_value_and_return_float_or_object(value)

        return Override(value_or_object)

    def apply_override(self, original_position_no_override, proposed_trade):
        """
        Apply an override to a position

        :param original_position_no_override: int
        :param proposed_trade: a trade object, with attr 'trade'
        :return: a trade object, with new attr 'trade'
        """

        if (
            isinstance(self._override, float)
            or self._override is override_close
            or self._override is override_none
        ):
            new_trade = self._apply_float_override(
                original_position_no_override, proposed_trade
            )

        elif self._override is override_reduce_only:
            new_trade = self._apply_reduce_only(
                original_position_no_override, proposed_trade
            )

        elif self._override is override_no_trading:
            new_trade = proposed_trade.replace_trade_only_use_for_unsubmitted_trades(
                0)

        else:
            raise Exception(
                "Override is %s don't know what to do!" % str(self._override)
            )

        return new_trade

    def _apply_float_override(
            self,
            original_position_no_override,
            proposed_trade):
        """
        Works if override value is float, or override_close (float value is 0.0) or override_none (float value is 1.0)

        :param original_position_no_override:
        :param proposed_trade:
        :return:
        """

        override_as_float = self.as_float()
        if override_as_float == 1.0:
            return proposed_trade

        desired_new_position = original_position_no_override + proposed_trade.trade
        override_new_position = int(
            np.floor(
                desired_new_position *
                override_as_float))

        new_trade_value = override_new_position - original_position_no_override

        proposed_trade.replace_trade_only_use_for_unsubmitted_trades(
            new_trade_value)

        return proposed_trade

    def _apply_reduce_only(
            self,
            original_position_no_override,
            proposed_trade):

        desired_new_position = original_position_no_override + proposed_trade.trade
        if sign(desired_new_position) != sign(original_position_no_override):
            # Closing trade only; don't allow sign to change
            new_trade_value = -original_position_no_override

        elif abs(desired_new_position) > abs(original_position_no_override):
            # Increasing trade not allowed
            new_trade_value = 0
        else:
            # Reducing trade and sign not changing, we'll allow
            new_trade_value = proposed_trade.trade

        proposed_trade.replace_trade_only_use_for_unsubmitted_trades(
            new_trade_value)

        return proposed_trade

    def __mul__(self, another_override):
        self_value = self._override
        another_value = another_override._override
        if another_value is override_no_trading or self_value is override_no_trading:
            return Override(override_no_trading)
        if another_value is override_close or self_value is override_close:
            return Override(override_close)
        if another_value is override_reduce_only or self_value is override_reduce_only:
            return Override(override_reduce_only)

        return Override(another_override.as_float() * self.as_float())


DEFAULT_OVERRIDE = Override(1.0)

strategy_dict = "strategies"
instrument_dict = "instruments"
strategy_instruments_dict = "strategies_instruments"


class overrideData(object):
    def __init__(self, log=logtoscreen("Overrides")):
        self.log = log
        self._overrides = dict(
            strategy={}, instrument={}, contract={}, strategy_instrument={}
        )

    def default_override(self):
        return DEFAULT_OVERRIDE

    def get_cumulative_override_for_strategy_and_instrument(
        self, strategy_name, instrument_code
    ):
        strategy_override = self.get_override_for_strategy(strategy_name)
        instrument_override = self.get_override_for_instrument(instrument_code)
        strategy_instrument_override = self.get_override_for_strategy_instrument(
            strategy_name, instrument_code)

        return strategy_override * instrument_override * strategy_instrument_override

    def get_override_for_strategy(self, strategy_name):
        return self._get_override_object_for_key(strategy_dict, strategy_name)

    def get_override_for_strategy_instrument(
            self, strategy_name, instrument_code):
        key = strategy_name + "/" + instrument_code
        return self._get_override_object_for_key(
            strategy_instruments_dict, key)

    def get_override_for_instrument(self, instrument_code):
        return self._get_override_object_for_key(
            instrument_dict, instrument_code)

    def update_override_for_strategy(self, strategy_name, new_override):
        self._update_override(strategy_dict, strategy_name, new_override)

    def update_override_for_strategy_instrument(
        self, strategy_name, instrument_code, new_override
    ):
        key = strategy_name + "/" + instrument_code
        self._update_override(strategy_instruments_dict, key, new_override)

    def update_override_for_instrument(self, instrument_code, new_override):
        self._update_override(instrument_dict, instrument_code, new_override)

    def get_dict_of_all_overrides(self):
        strategy_dict = self.get_dict_of_strategies_with_overrides()
        strategy_instrument_dict = self.get_dict_of_strategy_instrument_with_overrides()
        instrument_dict = self.get_dict_of_instruments_with_overrides()

        all_overrides = {**strategy_dict, **strategy_instrument_dict, **instrument_dict}

        return all_overrides

    def get_dict_of_strategies_with_overrides(self):
        return self._get_dict_of_items_with_overrides(strategy_dict)

    def get_dict_of_strategy_instrument_with_overrides(self):
        return self._get_dict_of_items_with_overrides(
            strategy_instruments_dict)

    def get_dict_of_instruments_with_overrides(self):
        return self._get_dict_of_items_with_overrides(instrument_dict)

    def _update_override(self, dict_name, key, new_override_object):
        self.log.msg("Updating override for %s %s to %s" %
                     (dict_name, key, new_override_object))
        override_dict = self._get_dict_of_items_with_overrides(dict_name)
        override_dict[key] = new_override_object

    def _get_override_object_for_key(self, dict_name, key):
        override_dict = self._get_dict_of_items_with_overrides(dict_name)
        override_object = override_dict.get(key, self.default_override())

        return override_object

    def _get_dict_of_items_with_overrides(self, dict_name):
        return self._overrides[dict_name]
