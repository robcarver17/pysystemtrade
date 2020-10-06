import numpy as np
import datetime
from collections import namedtuple

from syscore.genutils import quickTimer
from syscore.objects import missing_data, arg_not_supplied


def analyse_tick_data_frame(tick_data, qty):
    if tick_data is missing_data:
        return missing_data
    tick = extract_final_row_of_tick_data_frame(tick_data)
    results = analyse_tick(tick, qty)

    return results


oneTick = namedtuple(
    "oneTick", [
        "bid_price", "ask_price", "bid_size", "ask_size"])
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


def extract_final_row_of_tick_data_frame(tick_data):
    if len(tick_data) == 0:
        return empty_tick
    bid_price = tick_data.priceBid[-1]
    ask_price = tick_data.priceAsk[-1]
    bid_size = tick_data.sizeBid[-1]
    ask_size = tick_data.sizeAsk[-1]

    return oneTick(bid_price, ask_price, bid_size, ask_size)


def analyse_tick(tick, qty):
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

    # Eg if we're buying this would be the bid quantity divided by ask quantity
    # If this number goes significantly above 1 it suggests there is significant buying pressure
    # If we're selling this would be ask quantity divided by bid quantity
    # Again, if it goes above 1 suggests more selling pressure
    imbalance_ratio = offside_qty / side_qty

    results = analysisTick(
        order,
        side_price,
        mid_price,
        offside_price,
        spread,
        side_qty,
        offside_qty,
        imbalance_ratio,
    )

    return results


def adverse_price_movement(qty, price_old, price_new):
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


class tickerObject(object):
    """
    Something that receives ticks from the broker

    We wrap it in this so have standard methods
    """

    def __init__(self, ticker, qty=arg_not_supplied):
        self._ticker = ticker
        self._qty = qty
        self._ticks = []

    def refresh(self):
        pass

    @property
    def reference_tick(self):
        ref = getattr(self, "_reference_tick", empty_tick)
        return ref

    @reference_tick.setter
    def reference_tick(self, reference_tick):
        self._reference_tick = reference_tick
        self._reference_tick_analysis = self.analyse_for_tick(reference_tick)

    @property
    def reference_tick_analysis(self):
        return self._reference_tick_analysis

    def clear_and_add_reference_as_first_tick(self, reference_tick):
        self._ticks = []
        self.reference_tick = reference_tick
        self.add_tick(reference_tick)

    @property
    def ticks(self):
        return self._ticks

    def last_tick(self):
        ticks = self.ticks
        if len(ticks) == 0:
            return empty_tick
        return ticks[-1]

    def add_tick(self, tick):
        self._ticks.append(tick)

    @property
    def ticker(self):
        return self._ticker

    @property
    def qty(self):
        qty = self._qty
        return qty

    def bid(self):
        raise NotImplementedError

    def ask(self):
        raise NotImplementedError

    def bid_size(self):
        raise NotImplementedError

    def ask_size(self):
        raise NotImplementedError

    def current_tick(self, require_refresh=True):
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

    def analyse_for_tick(self, tick=arg_not_supplied, qty=arg_not_supplied):
        if qty is arg_not_supplied:
            qty = self.qty
        if tick is arg_not_supplied:
            tick = self.current_tick()

        if tick is missing_data or qty is arg_not_supplied:
            return missing_data

        results = analyse_tick(tick, qty)

        return results

    def wait_for_valid_bid_and_ask_and_return_current_tick(
            self, wait_time_seconds=10):
        waiting = True
        timer = quickTimer(wait_time_seconds)
        while waiting:
            if timer.finished:
                return missing_data
            self.refresh()
            last_bid = self.bid()
            last_ask = self.ask()
            last_bid_is_valid = not np.isnan(last_bid)
            last_ask_is_valid = not np.isnan(last_ask)

            if last_bid_is_valid and last_ask_is_valid:
                break

        current_tick = self.current_tick(require_refresh=False)

        return current_tick

    def adverse_price_movement_vs_reference(self):
        reference_offside_price = self.reference_offside_price
        current_offside_price = self.current_offside_price

        result = adverse_price_movement(
            self.qty, reference_offside_price, current_offside_price
        )

        return result

    def latest_imbalance_ratio(self):
        last_tick_analysis = self.current_tick_analysis
        return last_tick_analysis.imbalance_ratio

    @property
    def reference_offside_price(self):
        reference_tick_analysis = self.reference_tick_analysis
        return reference_tick_analysis.offside_price

    @property
    def last_offside_price(self):
        last_tick_analysis = self.last_tick_analysis

        return last_tick_analysis.offside_price

    @property
    def last_tick_analysis(self):
        last_tick = self.last_tick()
        analysis = self.analyse_for_tick(last_tick)
        return analysis

    @property
    def current_offside_price(self):
        current_tick_analysis = self.current_tick_analysis

        return current_tick_analysis.offside_price

    @property
    def current_side_price(self):
        current_tick_analysis = self.current_tick_analysis

        return current_tick_analysis.side_price

    @property
    def current_tick_analysis(self):
        current_tick = self.current_tick()
        analysis = self.analyse_for_tick(current_tick)
        return analysis
