from calendar import day_name
from copy import copy
from typing import Dict, List
import datetime
from dataclasses import dataclass

from syscore.dateutils import SECONDS_PER_HOUR
from syscore.objects import named_object

MIDNIGHT = datetime.time(0,0)


@dataclass()
class openingTimesAnyDay():
    opening_time: datetime.time
    closing_time: datetime.time

    def as_list(self):
        return [self.opening_time, self.closing_time]

    @classmethod
    def create_zero_length(cls):
        return cls(MIDNIGHT, MIDNIGHT)

    def not_zero_length(self) ->bool:
        return not self.is_zero_length()

    def is_zero_length(self) -> bool:
        return self.opening_time == self.closing_time

    def intersect_with_list(self, list_of_open_times: 'listOfOpeningTimesAnyDay') -> 'listOfOpeningTimesAnyDay':

        intersected_list = []
        for open_time in list_of_open_times:
            intersection = self.intersect_with_open_time(open_time)
            if intersection.not_zero_length():
                intersected_list.append(intersection)

        return listOfOpeningTimesAnyDay(intersected_list)

    def intersect_with_open_time(self, open_time: 'openingTimesAnyDay') -> 'openingTimesAnyDay':
        self_as_list = self.as_list()
        other_as_list = open_time.as_list()

        intervals = intersection_intervals([self_as_list, other_as_list])

        if len(intervals)==0:
            return openingTimesAnyDay.create_zero_length()

        return openingTimesAnyDay(intervals[0], intervals[1])


    def add_date(self, some_date: datetime.date) -> 'openingTimes':
        return openingTimes(
            datetime.datetime.combine(some_date, self.opening_time),
            datetime.datetime.combine(some_date, self.closing_time)
        )

    def as_simple_list(self) -> list:
        return [time_to_string(self.opening_time),
                time_to_string(self.closing_time)]

    @classmethod
    def from_simple_list(cls, simple_list: List[str]):
        opening_time = time_from_string(simple_list[0])
        closing_time = time_from_string(simple_list[1])
        return cls(opening_time, closing_time)

def time_to_string(time: datetime.time):
    return time.strftime("%H:%M")

def time_from_string(time_string: str):
    split_string = time_string.split(":")

    return datetime.time(int(split_string[0]),
                         int(split_string[1]))

class listOfOpeningTimesAnyDay(list):
    def __init__(self, list_of_times: List[openingTimesAnyDay]):
        super().__init__(list_of_times)

    def not_zero_length(self)-> bool:
        return len(self)>0

    def intersect(self, list_of_times: 'listOfOpeningTimesAnyDay') -> 'listOfOpeningTimesAnyDay':
        intersected_list = []
        for open_time in self:
            intersection = open_time.intersect_with_list(list_of_times)
            if intersection.not_zero_length():
                intersected_list.append(intersection)

        return listOfOpeningTimesAnyDay(intersected_list)


    def add_date(self, some_date: datetime.date):
        return listOfOpeningTimes([
            open_time.add_date(some_date)
            for open_time in self
        ])

    def to_simple_list(self) -> list:
        simple_list = [
            opening_times.as_simple_list()
            for opening_times in self
        ]

        return simple_list

    @classmethod
    def from_simple_list(cls, simple_list: list):
        # length zero means no opening hours
        if len(simple_list)==0:
            return cls([])
        ## this could be a nested list of lists, or just a single entry open/close
        if type(simple_list[0]) is not list:
            ## not nested, make it nested
            simple_list = [simple_list]

        list_of_times = [
            openingTimesAnyDay.from_simple_list(
                opening_times
            )
            for opening_times in simple_list
        ]
        return cls(list_of_times)



class weekdayDictOflistOfOpeningTimesAnyDay(dict):
    def __init__(self, dict_of_list_of_times: Dict[str, listOfOpeningTimesAnyDay]):
        super().__init__(dict_of_list_of_times)

    def intersect(self, weekday_dict_of_list_of_open_times) -> 'weekdayDictOflistOfOpeningTimesAnyDay':
        return intersection_weekday_dict_of_list_of_open_times\
                        (self,
                        weekday_dict_of_list_of_open_times)

    def to_simple_dict(self)-> dict:
        simple_dict = dict(
            [
                (
                    weekday_name,
                    self[weekday_name].to_simple_list()
                )

            for weekday_name in list(day_name)
            ]
        )

        return simple_dict

    @classmethod
    def from_simple_dict(cls, simple_dict: dict) -> 'weekdayDictOflistOfOpeningTimesAnyDay':
        if type(simple_dict) is list:
            ## if not specified per day
            return weekday_dict_of_opening_times_from_simple_list(simple_dict)
        else:
            ## if specified per day
            return weekday_dict_of_opening_times_from_simple_dict(simple_dict)

def intersection_weekday_dict_of_list_of_open_times\
            (first_dict: weekdayDictOflistOfOpeningTimesAnyDay,
            second_dict: weekdayDictOflistOfOpeningTimesAnyDay) -> weekdayDictOflistOfOpeningTimesAnyDay:

    new_dict = dict(
        [
            (weekday,
             first_dict[weekday].intersect(second_dict[weekday]))
            for weekday in list(day_name)
        ]
    )

    return weekdayDictOflistOfOpeningTimesAnyDay(new_dict)

def weekday_dict_of_opening_times_from_simple_dict(simple_dict: dict) -> weekdayDictOflistOfOpeningTimesAnyDay:
    weekday_dict = dict(
            [
                (
                    weekday_name,
                    listOfOpeningTimesAnyDay.from_simple_list(
                        simple_dict.get(weekday_name, [])
                    )
                )

                for weekday_name in list(day_name)
            ]
        )

    return weekdayDictOflistOfOpeningTimesAnyDay(weekday_dict)

def weekday_dict_of_opening_times_from_simple_list(simple_list: list) -> weekdayDictOflistOfOpeningTimesAnyDay:
    weekday_dict = dict(
            [
                (
                    weekday_name,
                    listOfOpeningTimesAnyDay.from_simple_list(
                        simple_list ## same opening times every day
                    )
                )

                for weekday_name in list(day_name)
            ]
        )

    return weekdayDictOflistOfOpeningTimesAnyDay(weekday_dict)


@dataclass()
class openingTimes():
    opening_time: datetime.datetime
    closing_time: datetime.datetime

    def as_list(self):
        return [self.opening_time, self.closing_time]

    @classmethod
    def create_zero_length_day(cls, some_date: datetime.date):
        midnight_on_date = following_midnight_of_datetime(some_date)
        return cls(midnight_on_date, midnight_on_date)

    def without_date(self) -> openingTimesAnyDay:
        return openingTimesAnyDay(self.opening_time.time(),
                                  self.closing_time.time())

    def not_zero_length(self):
        return not self.zero_length()

    def zero_length(self):
        return self.opening_time==self.closing_time

    def okay_to_trade_now(self) -> bool:
        datetime_now = datetime.datetime.now()
        if datetime_now >= self.opening_time and datetime_now <= self.closing_time:
            return True
        else:
            return False

    def hours_left_before_market_close(self) -> float:
        if not self.okay_to_trade_now():
            # market closed
            return 0

        datetime_now = datetime.datetime.now()
        time_left = self.closing_time - datetime_now
        seconds_left = time_left.total_seconds()
        hours_left = float(seconds_left) / SECONDS_PER_HOUR

        return hours_left

    def less_than_N_hours_left(self, N_hours: float = 1.0) -> bool:
        hours_left = self.hours_left_before_market_close()
        if hours_left < N_hours:
            return True
        else:
            return False

    def intersect_with_list_of_open_times_any_day(self,
                            saved_hours_for_weekday: listOfOpeningTimesAnyDay) -> 'listOfOpeningTimes':
        opening_date = self.opening_time.date()
        list_of_all_hours_to_intersect = saved_hours_for_weekday.add_date(opening_date)

        return self.intersect_with_list_of_open_times(list_of_all_hours_to_intersect)

    def intersect_with_list_of_open_times(self,
                                        list_of_open_times: 'listOfOpeningTimes') -> 'listOfOpeningTimes':

        intersected_list = []
        for open_time in list_of_open_times:
            intersection = self.intersect_with_open_time(open_time)
            if intersection.not_zero_length():
                intersected_list.append(intersection)

        return listOfOpeningTimes(intersected_list)

    def intersect_with_open_time(self, open_time: 'openingTimes') -> 'openingTimes':
        self_as_list = self.as_list()
        other_as_list = open_time.as_list()

        intervals = intersection_intervals([self_as_list, other_as_list])

        if len(intervals)==0:
            return openingTimes.create_zero_length_day(self.opening_time.date())

        return openingTimes(intervals[0], intervals[1])


def intersection_intervals(intervals):
    start, end = intervals.pop()
    while intervals:
         start_temp, end_temp = intervals.pop()
         start = max(start, start_temp)
         end = min(end, end_temp)

    if end<start:
        return []
    return [start, end]

class listOfOpeningTimes(list):
    def __init__(self, list_of_times: List[openingTimes]):
        super().__init__(list_of_times)

    def remove_zero_length_from_opening_times(self):
        list_of_opening_times = [opening_time for opening_time in self
                                 if opening_time.not_zero_length()]
        list_of_opening_times = listOfOpeningTimes(list_of_opening_times)
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
                if check_period.less_than_N_hours_left(N_hours=N_hours):
                    return True
                else:
                    return False
            else:
                # move on to next period
                continue

        # market closed, we treat that as 'less than one hour left'
        return True

    def create_weekly_dict_of_opening_times(self) -> weekdayDictOflistOfOpeningTimesAnyDay:
        return create_weekly_dict_of_opening_times(self)



def create_weekly_dict_of_opening_times(list_of_opening_times: listOfOpeningTimes) -> weekdayDictOflistOfOpeningTimesAnyDay:
    weekly_list_of_opening_times = dict(
        [
            (
                day_name[daynumber],
                create_opening_times_for_day(daynumber=daynumber,
                    list_of_opening_times=list_of_opening_times)
            )
            for daynumber in range(7)
        ]
    )

    return weekdayDictOflistOfOpeningTimesAnyDay(weekly_list_of_opening_times)


def create_opening_times_for_day(daynumber: int,
                                 list_of_opening_times: listOfOpeningTimes) \
                                -> listOfOpeningTimesAnyDay:

    opening_times_for_day = []
    remaining_opening_times_to_parse = copy(list_of_opening_times)
    while len(remaining_opening_times_to_parse)>0:
        next_opening_time = remaining_opening_times_to_parse.pop(0)
        parsed_open_time = parse_open_time_for_day(daynumber, next_opening_time)
        if parsed_open_time is not_open_today:
            continue

        opening_times_for_day.append(parsed_open_time)

    return listOfOpeningTimesAnyDay(opening_times_for_day)

not_open_today = named_object("Not open today")


def parse_open_time_for_day(daynumber: int, next_opening_time: openingTimes) -> openingTimesAnyDay:
    daynumber_open = next_opening_time.opening_time.weekday()
    daynumber_close = next_opening_time.closing_time.weekday()

    time_of_opening_time = next_opening_time.opening_time.time()
    time_of_closing_time = next_opening_time.closing_time.time()

    if daynumber_close!=daynumber and daynumber_open!=daynumber:
        return not_open_today

    if daynumber_open == daynumber_close == daynumber:
        return openingTimesAnyDay(
                time_of_opening_time,
                time_of_closing_time
            )

    if daynumber_open == daynumber and daynumber_close!=daynumber:
        return openingTimesAnyDay(
                time_of_opening_time,
                MIDNIGHT
            )

    if daynumber_open!=daynumber and daynumber_close == daynumber:
        return openingTimesAnyDay(
                MIDNIGHT,
                time_of_closing_time
            )

    # should never get here
    raise Exception("Can't handle %d and %s" % (daynumber,next_opening_time))


class dictOfDictOfWeekdayOpeningTimes(dict):
    ## keys are instruments, valuesa are lists of opening times
    def __init__(self, dict_of_dict_of_times: Dict[str, weekdayDictOflistOfOpeningTimesAnyDay]):
        super().__init__(dict_of_dict_of_times)

    def to_simple_dict(self) -> dict:
        ## allows yaml write
        simple_dict_of_weekday_opening_times = dict(
            [
                (instrument_code,
                 self[instrument_code].to_simple_dict())

            for instrument_code in list(self.keys())
            ]
        )

        return simple_dict_of_weekday_opening_times

    @classmethod
    def from_simple_dict(cls, simple_dict: dict):
        dict_of_weekday_opening_times = dict(
            [
                (instrument_code,
                 weekdayDictOflistOfOpeningTimesAnyDay.from_simple_dict(
                     simple_dict[instrument_code])
                 )

            for instrument_code in list(simple_dict.keys())
            ]
        )

        return cls(dict_of_weekday_opening_times)



class dictOfOpeningTimes(dict):
    ## keys are instruments, values are lists of opening times
    def __init__(self, dict_of_list_of_times: Dict[str, listOfOpeningTimes]):
        super().__init__(dict_of_list_of_times)

    def weekday_opening_times(self) -> dictOfDictOfWeekdayOpeningTimes:
        dict_of_weekday_opening_times = dict(
            [
                (instrument_code,
                 self[instrument_code].create_weekly_dict_of_opening_times())

            for instrument_code in list(self.keys())
            ]
        )

        return dictOfDictOfWeekdayOpeningTimes(dict_of_weekday_opening_times)

def adjust_trading_hours_conservatively(
    trading_hours: listOfOpeningTimes,
        conservative_times: openingTimesAnyDay
) -> listOfOpeningTimes:

    new_trading_hours = [
        adjust_single_day_conservatively(single_days_hours, conservative_times)
        for single_days_hours in trading_hours
    ]
    new_trading_hours = listOfOpeningTimes(new_trading_hours)
    new_trading_hours_remove_zeros = new_trading_hours.remove_zero_length_from_opening_times()

    return new_trading_hours_remove_zeros


def adjust_single_day_conservatively(
    single_days_hours: openingTimes,
        conservative_times: openingTimesAnyDay
    ) -> openingTimes:

    adjusted_start_datetime = adjust_start_time_conservatively(
        single_days_hours.opening_time, conservative_times.opening_time
    )
    adjusted_end_datetime = adjust_end_time_conservatively(
        single_days_hours.closing_time, conservative_times.closing_time
    )

    if adjusted_end_datetime<adjusted_start_datetime:
        ## Whoops
        adjusted_end_datetime = adjusted_start_datetime

    return openingTimes(adjusted_start_datetime, adjusted_end_datetime)


def adjust_start_time_conservatively(
    start_datetime: datetime.datetime, start_conservative: datetime.time
) -> datetime.datetime:
    time_part_for_start = start_datetime.time()
    conservative_time = max(time_part_for_start, start_conservative)
    start_conservative_datetime = adjust_date_conservatively(
        start_datetime, conservative_time
    )
    return start_conservative_datetime


def adjust_end_time_conservatively(
    end_datetime: datetime.datetime, end_conservative: datetime.time
) -> datetime.datetime:

    time_part_for_end = end_datetime.time()
    conservative_time = min(time_part_for_end, end_conservative)
    end_conservative_datetime = adjust_date_conservatively(
        end_datetime, conservative_time
    )
    return end_conservative_datetime


def adjust_date_conservatively(
    datetime_to_be_adjusted: datetime.datetime, conservative_time: datetime.time
) -> datetime.datetime:

    return datetime.datetime.combine(datetime_to_be_adjusted.date(), conservative_time)


def intersecting_trading_hours(list_of_opening_times: listOfOpeningTimes,
        saved_trading_hours: weekdayDictOflistOfOpeningTimesAnyDay
    ) -> listOfOpeningTimes:

    list_of_intersecting_hours = []
    for opening_times in list_of_opening_times:
        intersected_hours = intersected_trading_hours(opening_times, saved_trading_hours)
        list_of_intersecting_hours = list_of_intersecting_hours + intersected_hours

    return listOfOpeningTimes(list_of_intersecting_hours)

def intersected_trading_hours(opening_times: openingTimes,
                              saved_trading_hours: weekdayDictOflistOfOpeningTimesAnyDay)\
        -> listOfOpeningTimes:

    trading_hours_open_weekday = opening_times.opening_time.weekday()
    trading_hours_close_weekday = opening_times.closing_time.weekday()

    if trading_hours_close_weekday!=trading_hours_open_weekday:
        first_day_hours, second_day_hours = split_trading_hours_into_two_weekdays(
            opening_times
        )
        list_of_opening_times = \
                intersecting_trading_hours(first_day_hours,
                                          saved_trading_hours)+   \
                intersecting_trading_hours(second_day_hours,
                                           saved_trading_hours)

        return listOfOpeningTimes(list_of_opening_times)

    ## We know that the hours will be on the same day now
    name_of_day = day_name[trading_hours_open_weekday]
    saved_hours_for_weekday = saved_trading_hours[name_of_day]
    intersected_hours = opening_times.intersect_with_list_of_open_times_any_day(saved_hours_for_weekday)

    return intersected_hours

def split_trading_hours_into_two_weekdays(opening_times: openingTimes) -> tuple:
    opening_time = opening_times.opening_time
    closing_time = opening_times.closing_time

    return tuple([openingTimes(opening_time,
                        following_midnight_of_datetime(opening_time)),
            openingTimes(preceeding_midnight_of_datetime(closing_time),
                         closing_time)
                 ])

def preceeding_midnight_of_datetime(some_datetime: datetime.datetime):
    return datetime.datetime.combine(some_datetime.date(), datetime.datetime.min.time())

def following_midnight_of_datetime(some_datetime: datetime.datetime):
    return preceeding_midnight_of_datetime(some_datetime + datetime.timedelta(days=1))


