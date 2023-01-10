import datetime
from dataclasses import dataclass
from typing import List

from syscore.dateutils import MIDNIGHT, time_to_string, time_from_string
from syscore.genutils import intersection_intervals
from sysobjects.production.trading_hours.trading_hours import (
    tradingHours,
    listOfTradingHours,
)


@dataclass()
class tradingHoursAnyDay:
    opening_time: datetime.time
    closing_time: datetime.time

    def intersect_with_list(
        self, list_of_open_times: "listOfTradingHoursAnyDay"
    ) -> "listOfTradingHoursAnyDay":
        intersected_list = []
        for open_time in list_of_open_times:
            intersection = self.intersect(open_time)
            if intersection.not_zero_length():
                intersected_list.append(intersection)

        return listOfTradingHoursAnyDay(intersected_list)

    def intersect(self, open_time: "tradingHoursAnyDay") -> "tradingHoursAnyDay":
        self_as_list = self.as_list()
        other_as_list = open_time.as_list()

        intervals = intersection_intervals([self_as_list, other_as_list])

        if len(intervals) == 0:
            return tradingHoursAnyDay.create_zero_length()

        return tradingHoursAnyDay(intervals[0], intervals[1])

    def add_date(self, some_date: datetime.date) -> "tradingHours":
        return tradingHours(
            datetime.datetime.combine(some_date, self.opening_time),
            datetime.datetime.combine(some_date, self.closing_time),
        )

    def as_simple_list(self) -> list:
        return [time_to_string(self.opening_time), time_to_string(self.closing_time)]

    @classmethod
    def from_simple_list(cls, simple_list: List[str]):
        opening_time = time_from_string(simple_list[0])
        closing_time = time_from_string(simple_list[1])
        return cls(opening_time, closing_time)

    def as_list(self):
        return [self.opening_time, self.closing_time]

    @classmethod
    def create_zero_length(cls):
        return cls(MIDNIGHT, MIDNIGHT)

    def not_zero_length(self) -> bool:
        return not self.is_zero_length()

    def is_zero_length(self) -> bool:
        return self.opening_time == self.closing_time


class listOfTradingHoursAnyDay(list):
    def __init__(self, list_of_times: List[tradingHoursAnyDay]):
        super().__init__(list_of_times)

    def intersect(
        self, list_of_times: "listOfTradingHoursAnyDay"
    ) -> "listOfTradingHoursAnyDay":
        intersected_list = []
        for open_time in self:
            intersection = open_time.intersect_with_list(list_of_times)
            if intersection.not_zero_length():
                intersected_list = intersected_list + intersection

        return listOfTradingHoursAnyDay(intersected_list)

    def add_date(self, some_date: datetime.date) -> listOfTradingHours:
        return listOfTradingHours([open_time.add_date(some_date) for open_time in self])

    def to_simple_list(self) -> list:
        simple_list = [opening_times.as_simple_list() for opening_times in self]

        return simple_list

    @classmethod
    def from_simple_list(cls, simple_list: list):
        # length zero means no opening hours
        if len(simple_list) == 0:
            return cls([])
        ## this could be a nested list of lists, or just a single entry open/close
        if type(simple_list[0]) is not list:
            ## not nested, make it nested
            simple_list = [simple_list]

        list_of_times = [
            tradingHoursAnyDay.from_simple_list(opening_times)
            for opening_times in simple_list
        ]
        return cls(list_of_times)

    def not_zero_length(self) -> bool:
        return len(self) > 0
