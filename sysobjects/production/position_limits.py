from syscore.genutils import sign
from sysexecution.orders.base_orders import Order
from sysexecution.trade_qty import tradeQuantity
from sysobjects.instruments import futuresInstrument
from sysobjects.production.tradeable_object import instrumentStrategy

NO_LIMIT = "No limit"


class positionLimit(object):
    def __init__(self, tradeable_object, position_limit: int):
        self._tradeable_object = tradeable_object
        if position_limit == NO_LIMIT:
            self._position_limit = NO_LIMIT
        else:
            self._position_limit = abs(position_limit)

    def __repr__(self):
        return "Position limit for %s is %s" % (str(self.key), str(self.position_limit))

    def minimum_position_limit(self, other_position_limit) -> int:
        if other_position_limit.no_limit:
            return self.position_limit

        if self.no_limit:
            return other_position_limit.no_limit

        return min(self.position_limit, other_position_limit.position_limit)

    @property
    def position_limit(self):
        return self._position_limit

    @property
    def tradeable_object(self):
        return self._tradeable_object

    @property
    def key(self):
        return self.tradeable_object.key

    @property
    def no_limit(self):
        return self.position_limit == NO_LIMIT


class positionLimitForInstrument(positionLimit):
    def __init__(self, instrument_code: str, position_limit: int):
        tradeable_object = futuresInstrument(instrument_code)
        super().__init__(tradeable_object, position_limit)

    @classmethod
    def no_limit(positionLimitForInstrument, instrument_code):
        return positionLimitForInstrument(instrument_code, NO_LIMIT)


class positionLimitForStrategyInstrument(positionLimit):
    def __init__(self, instrument_strategy: instrumentStrategy, position_limit: int):
        super().__init__(instrument_strategy, position_limit)

    @classmethod
    def no_limit(
        positionLimitForStrategyInstrument, instrument_strategy: instrumentStrategy
    ):
        return positionLimitForStrategyInstrument(instrument_strategy, NO_LIMIT)


class positionLimitAndPosition(object):
    def __init__(self, position_limit_object: positionLimit, position: int):
        self._position_limit_object = position_limit_object
        self._position = position

    def __repr__(self):
        return "Position limit for %s is %s with current position %d" % (
            str(self.key),
            str(self.position_limit),
            self.position,
        )

    @property
    def position(self):
        return self._position

    @property
    def position_limit(self):
        return self._position_limit_object.position_limit

    @property
    def spare(self) -> float:
        if self.position_limit == NO_LIMIT:
            return 9999999

        return self.position_limit - abs(self.position)

    @property
    def key(self):
        return self._position_limit_object.key

    def apply_position_limit_to_order(self, order: Order) -> Order:
        if self.position_limit == NO_LIMIT:
            return order
        position = self.position
        position_limit = self.position_limit

        possible_trade = apply_position_limit_to_order(
            position=position, position_limit=position_limit, order=order
        )

        return possible_trade


def apply_position_limit_to_order(
    position: int, position_limit: int, order: Order
) -> Order:

    ## POSIITON LIMITS CAN ONLY BE APPLIED TO SINGLE LEG TRADES, EG INSTRUMENT ORDERS
    proposed_trade = order.as_single_trade_qty_or_error()
    possible_trade = apply_position_limit_to_single_leg_trade(
        position=position,
        position_limit=position_limit,
        proposed_trade=proposed_trade,
    )

    possible_trade_as_trade_qty = tradeQuantity(possible_trade)

    order = order.replace_required_trade_size_only_use_for_unsubmitted_trades(
        possible_trade_as_trade_qty
    )

    return order


def apply_position_limit_to_single_leg_trade(
    position: int, position_limit: int, proposed_trade: int
) -> int:
    """
    >>> apply_position_limit_to_single_leg_trade(1, 1, 0)
    0
    >>> apply_position_limit_to_single_leg_trade(5, 1, 0)
    -4
    >>> apply_position_limit_to_single_leg_trade(0, 3, 1)
    1
    >>> apply_position_limit_to_single_leg_trade(0, 3, 2)
    2
    >>> apply_position_limit_to_single_leg_trade(0, 3, 3)
    3
    >>> apply_position_limit_to_single_leg_trade(0, 3, 4)
    3
    >>> apply_position_limit_to_single_leg_trade(0, 3, -1)
    -1
    >>> apply_position_limit_to_single_leg_trade(0, 3, -2)
    -2
    >>> apply_position_limit_to_single_leg_trade(0, 3, -3)
    -3
    >>> apply_position_limit_to_single_leg_trade(0, 3, -4)
    -3
    >>> apply_position_limit_to_single_leg_trade(2, 3, 1)
    1
    >>> apply_position_limit_to_single_leg_trade(2, 3, 2)
    1
    >>> apply_position_limit_to_single_leg_trade(2, 3, -2)
    -2
    >>> apply_position_limit_to_single_leg_trade(2, 3, -4)
    -4
    >>> apply_position_limit_to_single_leg_trade(2, 3, -5)
    -5
    >>> apply_position_limit_to_single_leg_trade(2, 3, -6)
    -5
    >>> apply_position_limit_to_single_leg_trade(5, 3, 2)
    -2
    >>> apply_position_limit_to_single_leg_trade(5, 3, -1)
    -2
    >>> apply_position_limit_to_single_leg_trade(5, 3, -2)
    -2
    >>> apply_position_limit_to_single_leg_trade(5, 3, -9)
    -8
    >>> apply_position_limit_to_single_leg_trade(2, 3, -4)
    -4
    >>> apply_position_limit_to_single_leg_trade(2, 3, -5)
    -5
    >>> apply_position_limit_to_single_leg_trade(2, 3, -6)
    -5
    >>> apply_position_limit_to_single_leg_trade(0, 3, 1)
    1
    >>> apply_position_limit_to_single_leg_trade(0, 3, -4)
    -3
    >>> apply_position_limit_to_single_leg_trade(-2, 3, -1)
    -1
    >>> apply_position_limit_to_single_leg_trade(-2, 3, -2)
    -1
    >>> apply_position_limit_to_single_leg_trade(-5, 3, -2)
    2
    >>> apply_position_limit_to_single_leg_trade(-5, 3, 1)
    2
    >>> apply_position_limit_to_single_leg_trade(-5, 3, 2)
    2
    >>> apply_position_limit_to_single_leg_trade(-5, 3, 7)
    7
    >>> apply_position_limit_to_single_leg_trade(-5, 3, 9)
    8
    >>> apply_position_limit_to_single_leg_trade(-3, 3, 7)
    6
    >>> apply_position_limit_to_single_leg_trade(3, 3, -7)
    -6
    >>> apply_position_limit_to_single_leg_trade(3, 0, -7)
    -3
    >>> apply_position_limit_to_single_leg_trade(3, 0, 0)
    -3
    >>> apply_position_limit_to_single_leg_trade(3, 0, 7)
    -3
    >>> apply_position_limit_to_single_leg_trade(-3, 0, 2)
    3
    >>> apply_position_limit_to_single_leg_trade(-3, 0, 4)
    3
    >>> apply_position_limit_to_single_leg_trade(-3, 0, -3)
    3
    >>> apply_position_limit_to_single_leg_trade(3, 1, 2)
    -2
    >>> apply_position_limit_to_single_leg_trade(3, 1, -2)
    -2
    >>> apply_position_limit_to_single_leg_trade(3, 1, -4)
    -4
    >>> apply_position_limit_to_single_leg_trade(3, 1, -5)
    -4

    """
    new_position = position + proposed_trade

    # position limit should be abs, but just in case...
    abs_position_limit = abs(position_limit)
    signed_position_limit = int(abs_position_limit * sign(new_position))

    trade_to_bring_position_in_line_with_position_limit = int(
        sign(position) * (abs_position_limit - abs(position))
    )

    if abs(new_position) <= abs_position_limit:
        ## new position is within limits
        return proposed_trade

    if position >= 0 and abs(position) <= abs_position_limit:
        ## Was okay, but won't be after trade
        ## We move to the limit, either long or short depending on what the trade wanted to do
        possible_new_position = signed_position_limit
        possible_trade = possible_new_position - position

        return possible_trade

    if position >= 0 and abs(position) > abs_position_limit:
        ## Was already too big
        if proposed_trade >= 0:
            # want to buy when already too big
            return trade_to_bring_position_in_line_with_position_limit

        if new_position > 0:
            ## selling, but sell isn't big enough to get within limits
            ## we don't increase the size of a trade
            return trade_to_bring_position_in_line_with_position_limit
        else:
            ## selling and gone out the other side
            possible_new_position = signed_position_limit
            possible_trade = possible_new_position - position

            return possible_trade

    if position < 0 and abs(position) <= abs_position_limit:
        ## Was okay, but won't be after trade
        ## We move to the limit, either long or short depending on what the trade wanted to do
        possible_new_position = signed_position_limit
        possible_trade = possible_new_position - position

        return possible_trade

    if position < 0 and abs(position) > abs_position_limit:
        ## Was already too big
        if proposed_trade < 0:
            # want to sell when already too big
            return trade_to_bring_position_in_line_with_position_limit
        if new_position < 0:
            ## buying but not big enough to get within limits
            return trade_to_bring_position_in_line_with_position_limit
        else:
            # buying and gone out the other side
            possible_new_position = signed_position_limit
            possible_trade = possible_new_position - position

            return possible_trade

    raise Exception(
        "Don't know how to handle original position %f proposed trade %f limit %f"
        % (position, proposed_trade, abs_position_limit)
    )
