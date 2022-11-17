from calendar import day_name
from copy import copy
from typing import Dict

from syscore.dateutils import MIDNIGHT, following_one_second_before_midnight_of_datetime, preceeding_midnight_of_datetime
from syscore.objects import named_object
from sysobjects.production.trading_hours.trading_hours import tradingHours, listOfTradingHours
from sysobjects.production.trading_hours.trading_hours_any_day import tradingHoursAnyDay, listOfTradingHoursAnyDay


class weekdayDictOflistOfOpeningTimesAnyDay(dict):
    def __init__(self, dict_of_list_of_times: Dict[str, listOfTradingHoursAnyDay]):
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
                    listOfTradingHoursAnyDay.from_simple_list(
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
                    listOfTradingHoursAnyDay.from_simple_list(
                        simple_list ## same opening times every day
                    )
                )

                for weekday_name in list(day_name)
            ]
        )

    return weekdayDictOflistOfOpeningTimesAnyDay(weekday_dict)


def create_weekly_dict_of_opening_times(list_of_opening_times: 'listOfTradingHours') -> weekdayDictOflistOfOpeningTimesAnyDay:
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
                                 list_of_opening_times: 'listOfTradingHours') \
                                -> listOfTradingHoursAnyDay:

    opening_times_for_day = []
    remaining_opening_times_to_parse = copy(list_of_opening_times)
    while len(remaining_opening_times_to_parse)>0:
        next_opening_time = remaining_opening_times_to_parse.pop(0)
        parsed_open_time = parse_open_time_for_day(daynumber, next_opening_time)
        if parsed_open_time is not_open_today:
            continue

        opening_times_for_day.append(parsed_open_time)

    return listOfTradingHoursAnyDay(opening_times_for_day)


not_open_today = named_object("Not open today")


def parse_open_time_for_day(daynumber: int, next_opening_time: tradingHours) -> tradingHoursAnyDay:
    daynumber_open = next_opening_time.opening_time.weekday()
    daynumber_close = next_opening_time.closing_time.weekday()

    time_of_opening_time = next_opening_time.opening_time.time()
    time_of_closing_time = next_opening_time.closing_time.time()

    if daynumber_close!=daynumber and daynumber_open!=daynumber:
        return not_open_today

    if daynumber_open == daynumber_close == daynumber:
        return tradingHoursAnyDay(
                time_of_opening_time,
                time_of_closing_time
            )

    if daynumber_open == daynumber and daynumber_close!=daynumber:
        return tradingHoursAnyDay(
                time_of_opening_time,
            MIDNIGHT
            )

    if daynumber_open!=daynumber and daynumber_close == daynumber:
        return tradingHoursAnyDay(
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
    def __init__(self, dict_of_list_of_times: Dict[str, listOfTradingHours]):
        super().__init__(dict_of_list_of_times)

    def weekday_opening_times(self) -> dictOfDictOfWeekdayOpeningTimes:
        dict_of_weekday_opening_times = dict(
            [
                (
                    instrument_code,
                 create_weekly_dict_of_opening_times(self[instrument_code])
                 )
            for instrument_code in list(self.keys())
            ]
        )

        return dictOfDictOfWeekdayOpeningTimes(dict_of_weekday_opening_times)



def intersection_of_weekly_and_specific_trading_hours(list_of_opening_times: listOfTradingHours,
                                                      saved_trading_hours: weekdayDictOflistOfOpeningTimesAnyDay
                                                      ) -> listOfTradingHours:

    list_of_intersecting_hours = []
    for opening_times in list_of_opening_times:
        intersected_hours = intersected_trading_hours(opening_times, saved_trading_hours)
        list_of_intersecting_hours = list_of_intersecting_hours + intersected_hours

    return listOfTradingHours(list_of_intersecting_hours)


def intersected_trading_hours(opening_times: tradingHours,
                              saved_trading_hours: weekdayDictOflistOfOpeningTimesAnyDay)\
        -> listOfTradingHours:

    trading_hours_open_weekday = opening_times.opening_time.weekday()
    trading_hours_close_weekday = opening_times.closing_time.weekday()

    if trading_hours_close_weekday!=trading_hours_open_weekday:
        first_day_hours, second_day_hours = split_trading_hours_into_two_weekdays(
            opening_times
        )
        list_of_opening_times = \
            intersection_of_weekly_and_specific_trading_hours(first_day_hours,
                                                              saved_trading_hours) + \
            intersection_of_weekly_and_specific_trading_hours(second_day_hours,
                                                              saved_trading_hours)

        return listOfTradingHours(list_of_opening_times)

    ## We know that the hours will be on the same day now
    name_of_day = day_name[trading_hours_open_weekday]
    saved_hours_for_weekday = saved_trading_hours[name_of_day]
    intersected_hours = intersect_with_list_of_open_times(opening_times,
                                                          saved_hours_for_weekday)

    return intersected_hours

def intersect_with_list_of_open_times_any_day(opening_times: tradingHours,
                                              saved_hours_for_weekday: listOfTradingHoursAnyDay) -> 'listOfTradingHours':
    opening_date = opening_times.opening_time.date()
    list_of_open_times = saved_hours_for_weekday.add_date(opening_date)
    intersection = intersect_with_list_of_open_times(opening_times,
                                                     list_of_open_times)

    return intersection

def intersect_with_list_of_open_times(opening_times: tradingHours,
                                      list_of_open_times: 'listOfTradingHours') -> 'listOfTradingHours':

    intersected_list = []
    for open_time in list_of_open_times:
        intersection = opening_times.intersect(open_time)
        if intersection.not_zero_length():
            intersected_list.append(intersection)

    return listOfTradingHours(intersected_list)



def split_trading_hours_into_two_weekdays(opening_times: tradingHours) -> tuple:
    opening_time = opening_times.opening_time
    closing_time = opening_times.closing_time

    return tuple([tradingHours(opening_time,
                               following_one_second_before_midnight_of_datetime(opening_time)),
                  tradingHours(preceeding_midnight_of_datetime(closing_time),
                               closing_time)
                  ])