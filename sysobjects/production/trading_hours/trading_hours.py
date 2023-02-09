import datetime
from dataclasses import dataclass
from typing import List

from syscore.dateutils import (
    following_one_second_before_midnight_of_date,
    SECONDS_PER_HOUR,
    following_one_second_before_midnight_of_datetime,
    preceeding_midnight_of_datetime,
)
from syscore.genutils import intersection_intervals
from syscore.constants import market_closed


@dataclass()
class tradingHours:
    opening_time: datetime.datetime
    closing_time: datetime.datetime

    @classmethod
    def create_zero_length_day(cls, some_date: datetime.date):
        midnight_on_date = following_one_second_before_midnight_of_date(some_date)
        return cls(midnight_on_date, midnight_on_date)

    def okay_to_trade_now(self) -> bool:
        datetime_now = datetime.datetime.now()
        if datetime_now >= self.opening_time and datetime_now <= self.closing_time:
            return True
        else:
            return False

    def less_than_N_hours_left(self, N_hours: float = 1.0) -> bool:
        hours_left = self.hours_left_before_market_close()
        if hours_left is market_closed:
            return market_closed

        if hours_left < N_hours:
            return True
        else:
            return False

    def hours_left_before_market_close(self) -> float:
        if not self.okay_to_trade_now():
            # market closed
            return market_closed

        datetime_now = datetime.datetime.now()
        time_left = self.closing_time - datetime_now
        seconds_left = time_left.total_seconds()
        hours_left = float(seconds_left) / SECONDS_PER_HOUR

        return hours_left

    def intersect(self, open_time: "tradingHours") -> "tradingHours":
        self_as_list = self.as_list()
        other_as_list = open_time.as_list()

        intervals = intersection_intervals([self_as_list, other_as_list])

        if len(intervals) == 0:
            return tradingHours.create_zero_length_day(self.opening_time.date())

        return tradingHours(intervals[0], intervals[1])

    def as_list(self):
        return [self.opening_time, self.closing_time]

    def not_zero_length(self):
        return not self.zero_length()

    def zero_length(self):
        return self.opening_time == self.closing_time


class listOfTradingHours(list):
    def __init__(self, list_of_times: List[tradingHours]):
        super().__init__(list_of_times)

    def intersect_with_trading_hours(
        self, other_trading_hours: tradingHours
    ) -> "listOfTradingHours":  #
        intersected_list = []
        for my_trading_hours in self:
            intersection = my_trading_hours.intersect(other_trading_hours)
            if intersection.not_zero_length():
                intersected_list.append(intersection)

        return listOfTradingHours(intersected_list)

    def remove_zero_length_from_opening_times(self):
        list_of_opening_times = [
            opening_time for opening_time in self if opening_time.not_zero_length()
        ]
        list_of_opening_times = listOfTradingHours(list_of_opening_times)
        return list_of_opening_times

    def okay_to_trade_now(self):
        for check_period in self:
            if check_period.okay_to_trade_now():
                # okay to trade if it's okay to trade on some date
                # don't need to check any more
                return True
        return False

    def less_than_N_hours_left(self, N_hours: float = 1.0):
        for check_period in self:
            if check_period.okay_to_trade_now():
                # market is open, but for how long?
                less_than_N_hours_left = check_period.less_than_N_hours_left(
                    N_hours=N_hours
                )

                if less_than_N_hours_left:
                    return True
                else:
                    return False
            else:
                # move on to next period
                continue

        return market_closed


def split_trading_hours_across_two_weekdays(
    opening_times: tradingHours,
) -> listOfTradingHours:
    opening_time = opening_times.opening_time
    closing_time = opening_times.closing_time

    first_day_hours = tradingHours(
        opening_time, following_one_second_before_midnight_of_datetime(opening_time)
    )

    second_day_hours = tradingHours(
        preceeding_midnight_of_datetime(closing_time), closing_time
    )

    return listOfTradingHours([first_day_hours, second_day_hours])
