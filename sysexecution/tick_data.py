from copy import copy
import numpy as np
import pandas as pd
from collections import namedtuple

from syscore.genutils import quickTimer
from syscore.exceptions import missingData
from syscore.constants import arg_not_supplied

TICK_REQUIRED_COLUMNS = ["priceAsk", "priceBid", "sizeAsk", "sizeBid"]


class dataFrameOfRecentTicks(pd.DataFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        columns = self.columns
        sorted_columns = sorted(columns)

        try:
            assert all([x == y for x, y in zip(sorted_columns, TICK_REQUIRED_COLUMNS)])
        except:
            raise Exception(
                "historical ticks should have columns %s" % str(TICK_REQUIRED_COLUMNS)
            )

    def average_bid_offer_spread(self, remove_negative=True) -> float:
        return average_bid_offer_spread(self, remove_negative=remove_negative)

    @classmethod
    def create_empty(dataFrameOfRecentTicks):
        return dataFrameOfRecentTicks(pd.DataFrame(columns=TICK_REQUIRED_COLUMNS))

    def is_empty(self) -> bool:
        return len(self) == 0


def analyse_tick_data_frame(
    tick_data: dataFrameOfRecentTicks,
    qty: int,
    forward_fill: bool = False,
    replace_qty_nans=False,
):

    if tick_data.is_empty():
        raise missingData("Tick data is empty")

    tick = extract_final_row_of_tick_data_frame(tick_data, forward_fill=forward_fill)
    results = analyse_tick(tick, qty, replace_qty_nans=replace_qty_nans)

    return results


oneTick = namedtuple("oneTick", ["bid_price", "ask_price", "bid_size", "ask_size"])
analysisTick = namedtuple(
    "analysisTick",
    [
        "order",
        "side_price",
        "mid_price",
        "offside_price",
        "spread",
        "side_qty",
        "offside_qty",
        "imbalance_ratio",
    ],
)

empty_tick = oneTick(np.nan, np.nan, np.nan, np.nan)


def extract_final_row_of_tick_data_frame(
    tick_data: pd.DataFrame, forward_fill=False
) -> oneTick:
    final_row = extract_nth_row_of_tick_data_frame(
        tick_data, row_id=-1, forward_fill=forward_fill
    )
    return final_row


def extract_nth_row_of_tick_data_frame(
    tick_data: pd.DataFrame, row_id: int, forward_fill=False
) -> oneTick:
    if len(tick_data) == 0:
        return empty_tick
    if forward_fill:
        filled_data = tick_data.ffill()
    else:
        filled_data = copy(tick_data)

    bid_price = filled_data.priceBid[row_id]
    ask_price = filled_data.priceAsk[row_id]
    bid_size = filled_data.sizeBid[row_id]
    ask_size = filled_data.sizeAsk[row_id]

    return oneTick(bid_price, ask_price, bid_size, ask_size)


def average_bid_offer_spread(
    tick_data: dataFrameOfRecentTicks, remove_negative: bool = True
) -> float:
    if tick_data.is_empty():
        raise missingData("Tick data is empty")
    all_spreads = tick_data.priceAsk - tick_data.priceBid
    if remove_negative:
        all_spreads[all_spreads < 0] = np.nan
    average_spread = all_spreads.mean(skipna=True)

    if np.isnan(average_spread):
        raise missingData("Unable to calculate avg spread")

    return average_spread


VERY_LARGE_IMBALANCE = 9999


def analyse_tick(tick: oneTick, qty: int, replace_qty_nans=False) -> analysisTick:
    mid_price = np.mean([tick.ask_price, tick.bid_price])
    spread = tick.ask_price - tick.bid_price

    is_buy = qty >= 0
    if is_buy:
        order = "B"
        side_price = tick.ask_price
        offside_price = tick.bid_price
        side_qty = tick.ask_size
        offside_qty = tick.bid_size
    else:
        order = "S"
        # Selling, normally at the bid
        side_price = tick.bid_price
        offside_price = tick.ask_price
        side_qty = tick.bid_size
        offside_qty = tick.ask_size

    if replace_qty_nans:
        side_qty = _zero_replace_nan(side_qty)
        offside_qty = _zero_replace_nan(offside_qty)

    # Eg if we're buying this would be the bid quantity divided by ask quantity
    # If this number goes significantly above 1 it suggests there is significant buying pressure
    # If we're selling this would be ask quantity divided by bid quantity
    # Again, if it goes above 1 suggests more selling pressure
    if side_qty == 0:
        imbalance_ratio = VERY_LARGE_IMBALANCE
    else:
        imbalance_ratio = offside_qty / side_qty

    results = analysisTick(
        order=order,
        side_price=side_price,
        mid_price=mid_price,
        offside_price=offside_price,
        spread=spread,
        side_qty=side_qty,
        offside_qty=offside_qty,
        imbalance_ratio=imbalance_ratio,
    )

    return results


def _zero_replace_nan(x):
    if np.isnan(x):
        return 0
    else:
        return x


class tickerObject(object):
    """
    Something that receives ticks from the broker

    We wrap it in this so have standard methods
    """

    def __init__(self, ticker, qty: int = arg_not_supplied):
        # 'ticker' will depend on the implementation
        self._ticker = ticker
        self._qty = qty
        self._ticks = []

    @property
    def ticker(self):
        return self._ticker

    @property
    def qty(self) -> int:
        qty = self._qty
        return qty

    @property
    def ticks(self) -> list:
        return self._ticks

    @property
    def reference_tick(self) -> oneTick:
        reference_tick = getattr(self, "_reference_tick", empty_tick)
        return reference_tick

    @reference_tick.setter
    def reference_tick(self, reference_tick: oneTick):
        self._reference_tick = reference_tick
        self._reference_tick_analysis = self.analyse_for_tick(reference_tick)

    @property
    def reference_tick_analysis(self):
        return self._reference_tick_analysis

    def clear_and_add_reference_as_first_tick(self, reference_tick: oneTick):
        self._ticks = []
        self.reference_tick = reference_tick
        self.add_tick(reference_tick)

    def last_tick(self) -> oneTick:
        ticks = self.ticks
        if len(ticks) == 0:
            return empty_tick
        return ticks[-1]

    def add_tick(self, tick: oneTick):
        self._ticks.append(tick)

    def current_tick(self, require_refresh=True) -> oneTick:
        if require_refresh:
            self.refresh()
        bid = self.bid()
        ask = self.ask()
        bid_size = self.bid_size()
        ask_size = self.ask_size()
        tick = oneTick(
            bid_price=bid, ask_price=ask, bid_size=bid_size, ask_size=ask_size
        )

        self.add_tick(tick)

        return tick

    def analyse_for_tick(
        self,
        tick: oneTick = arg_not_supplied,
        qty: int = arg_not_supplied,
        replace_qty_nans=False,
    ):
        if qty is arg_not_supplied:
            qty = self.qty

        if tick is arg_not_supplied:
            tick = self.current_tick()

        if qty is arg_not_supplied:
            raise missingData("Quantity must be specified")

        results = analyse_tick(tick, qty, replace_qty_nans=replace_qty_nans)

        return results

    def wait_for_valid_bid_and_ask_and_analyse_current_tick(
        self, qty: int = arg_not_supplied, wait_time_seconds: int = 10
    ) -> oneTick:

        current_tick = self.wait_for_valid_bid_and_ask_and_return_current_tick(
            wait_time_seconds=wait_time_seconds
        )
        analysis = self.analyse_for_tick(current_tick, qty=qty)

        return analysis

    def wait_for_valid_bid_and_ask_and_return_current_tick(
        self, wait_time_seconds: int = 10
    ) -> oneTick:
        waiting = True
        timer = quickTimer(wait_time_seconds)
        while waiting:
            if timer.finished:
                raise missingData
            self.refresh()
            last_bid = self.bid()
            last_ask = self.ask()
            last_bid_is_valid = not np.isnan(last_bid)
            last_ask_is_valid = not np.isnan(last_ask)

            if last_bid_is_valid and last_ask_is_valid:
                break

        current_tick = self.current_tick(require_refresh=False)

        return current_tick

    def adverse_price_movement_vs_reference(self) -> bool:
        reference_offside_price = self.reference_offside_price
        current_offside_price = self.current_offside_price

        result = adverse_price_movement(
            self.qty, reference_offside_price, current_offside_price
        )

        return result

    def latest_imbalance_ratio(self) -> float:
        last_tick_analysis = self.current_tick_analysis
        return last_tick_analysis.imbalance_ratio

    @property
    def reference_offside_price(self) -> float:
        reference_tick_analysis = self.reference_tick_analysis
        return reference_tick_analysis.offside_price

    @property
    def last_offside_price(self) -> float:
        last_tick_analysis = self.last_tick_analysis

        return last_tick_analysis.offside_price

    @property
    def last_tick_analysis(self) -> analysisTick:
        last_tick = self.last_tick()
        analysis = self.analyse_for_tick(last_tick)
        return analysis

    @property
    def current_offside_price(self) -> float:
        current_tick_analysis = self.current_tick_analysis

        return current_tick_analysis.offside_price

    @property
    def current_side_price(self) -> float:
        current_tick_analysis = self.current_tick_analysis

        return current_tick_analysis.side_price

    @property
    def current_tick_analysis(self) -> analysisTick:
        current_tick = self.current_tick()
        analysis = self.analyse_for_tick(current_tick)
        return analysis

    def bid(self):
        raise NotImplementedError

    def ask(self):
        raise NotImplementedError

    def bid_size(self):
        raise NotImplementedError

    def ask_size(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError


def adverse_price_movement(qty: int, price_old: float, price_new: float) -> bool:
    if qty > 0:
        if price_new > price_old:
            return True
        else:
            return False

    else:
        if price_new < price_old:
            return True
        else:
            return False
