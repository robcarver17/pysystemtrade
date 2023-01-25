import numpy as np

from syscore.genutils import sign
from syscore.constants import named_object
from sysexecution.orders.base_orders import Order
from sysexecution.trade_qty import tradeQuantity

override_close = named_object("Close")
override_no_trading = named_object("No trading")
override_reduce_only = named_object("Reduce only")
override_none = named_object("No override")
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
        if value in override_dict.keys():
            override_value = value
        elif isinstance(value, float) or isinstance(value, int):
            assert value >= 0.0
            assert value <= 1.0
            override_value = float(value)
        else:
            raise Exception(
                "Override must be between 0.0 and 1.0, or one of the following objects %s"
                % str(override_dict)
            )

        self._override = override_value

    def __repr__(self):
        return "Override %s" % str(self.override_value)

    @property
    def override_value(self):
        return self._override

    def __eq__(self, other):
        return self.override_value == other.override_value

    def as_float(self):
        assert self.is_float_like()
        value = self.override_value
        if value in override_dict.keys():
            return override_dict[value]
        else:
            return value

    def as_numeric_value(self):
        value = self.override_value
        if value in override_dict.keys():
            return override_dict[value]
        else:
            return value

    def is_no_override(self):
        if self.override_value is override_none:
            return True

        if self.override_value == 1.0:
            return True

        return False

    def is_float_like(self):
        override_value = self.override_value
        """
        override_close and override_none are equivalent to float values of 0 and 1 respectively
        """
        if (
            isinstance(override_value, float)
            or override_value is override_close
            or override_value is override_none
        ):
            return True
        else:
            return False

    @classmethod
    def from_numeric_value(Override, value):
        value_or_object = lookup_value_and_return_float_or_object(value)

        return Override(value_or_object)

    def apply_override(
        self, original_position_no_override: int, proposed_trade: Order
    ) -> Order:
        """
        Apply an override to a position

        :param original_position_no_override: int
        :param proposed_trade: a trade object, with attr 'trade'
        :return: a trade object, with new attr 'trade'
        """
        override_value = self.override_value
        if self.is_float_like():
            override_as_float = self.as_float()
            new_trade = _apply_float_override(
                override_as_float, original_position_no_override, proposed_trade
            )

        elif override_value is override_reduce_only:
            new_trade = _apply_reduce_only(
                original_position_no_override, proposed_trade
            )

        elif override_value is override_no_trading:
            new_trade = _apply_no_trading(proposed_trade)

        else:
            raise Exception(
                "Override is %s don't know what to do!" % str(self._override)
            )

        return new_trade

    def __mul__(self, another_override):
        self_value = self.override_value
        another_value = another_override.override_value
        if another_value is override_no_trading or self_value is override_no_trading:
            return Override(override_no_trading)
        if another_value is override_close or self_value is override_close:
            return Override(override_close)
        if another_value is override_reduce_only or self_value is override_reduce_only:
            return Override(override_reduce_only)

        assert self.is_float_like()
        assert another_override.is_float_like()

        return Override(another_override.as_float() * self.as_float())


DEFAULT_OVERRIDE = Override(1.0)
NO_TRADE_OVERRIDE = Override(override_no_trading)
REDUCE_ONLY_OVERRIDE = Override(override_reduce_only)
CLOSE_OVERRIDE = Override(override_close)


def _apply_float_override(
    override_as_float: float, original_position_no_override: int, proposed_trade: Order
) -> Order:
    """
    Works if override value is float, or override_close (float value is 0.0) or override_none (float value is 1.0)

    :param original_position_no_override:
    :param proposed_trade:
    :return:
    """

    if override_as_float == 1.0:
        return proposed_trade

    desired_new_position = (
        original_position_no_override
        + proposed_trade.trade.as_single_trade_qty_or_error()
    )
    override_new_position = int(np.floor(desired_new_position * override_as_float))

    new_trade_value = override_new_position - original_position_no_override

    new_trade = (
        proposed_trade.replace_required_trade_size_only_use_for_unsubmitted_trades(
            tradeQuantity(new_trade_value)
        )
    )

    return new_trade


def _apply_reduce_only(
    original_position_no_override: int, proposed_trade: Order
) -> Order:

    proposed_trade_value = proposed_trade.trade.as_single_trade_qty_or_error()
    desired_new_position = original_position_no_override + proposed_trade_value
    if sign(desired_new_position) != sign(original_position_no_override):
        # Wants sign to change, we convert into a pure closing trade
        new_trade_value = -original_position_no_override

    elif abs(desired_new_position) > abs(original_position_no_override):
        # Increasing trade not allowed, zero trade
        new_trade_value = 0
    else:
        # Reducing trade and sign not changing, we'll allow
        new_trade_value = proposed_trade_value

    new_trade = (
        proposed_trade.replace_required_trade_size_only_use_for_unsubmitted_trades(
            tradeQuantity(new_trade_value)
        )
    )

    return new_trade


def _apply_no_trading(proposed_trade: Order):
    new_trade = (
        proposed_trade.replace_required_trade_size_only_use_for_unsubmitted_trades(
            tradeQuantity(0)
        )
    )

    return new_trade
