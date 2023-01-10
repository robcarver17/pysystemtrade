from calendar import day_name
from typing import Dict

from sysobjects.production.trading_hours.trading_hours_any_day import (
    listOfTradingHoursAnyDay,
)

list_of_weekday_names = list(day_name)


class weekdayDictOfListOfTradingHoursAnyDay(dict):
    def __init__(self, dict_of_list_of_times: Dict[str, listOfTradingHoursAnyDay]):
        super().__init__(dict_of_list_of_times)

    def intersect(
        self,
        weekday_dict_of_list_of_open_times: "weekdayDictOfListOfTradingHoursAnyDay",
    ) -> "weekdayDictOfListOfTradingHoursAnyDay":

        return intersection_weekday_dict_of_list_of_trading_hours_any_day(
            self, weekday_dict_of_list_of_open_times
        )

    def to_simple_dict(self) -> dict:
        simple_dict = dict(
            [
                (weekday_name, self[weekday_name].to_simple_list())
                for weekday_name in list_of_weekday_names
            ]
        )

        return simple_dict

    @classmethod
    def from_simple_dict(
        cls, simple_dict: dict
    ) -> "weekdayDictOfListOfTradingHoursAnyDay":
        if type(simple_dict) is list:
            ## if not specified per day
            return weekday_dict_of_trading_hours_from_simple_list(simple_dict)
        else:
            ## if specified per day
            return weekday_dict_of_trading_hour_from_simple_dict(simple_dict)

    @classmethod
    def create_empty(cls) -> "weekdayDictOfListOfTradingHoursAnyDay":
        return cls.from_simple_dict({})


def intersection_weekday_dict_of_list_of_trading_hours_any_day(
    first_dict: weekdayDictOfListOfTradingHoursAnyDay,
    second_dict: weekdayDictOfListOfTradingHoursAnyDay,
) -> weekdayDictOfListOfTradingHoursAnyDay:

    new_dict = dict(
        [
            (weekday, first_dict[weekday].intersect(second_dict[weekday]))
            for weekday in list_of_weekday_names
        ]
    )

    return weekdayDictOfListOfTradingHoursAnyDay(new_dict)


def weekday_dict_of_trading_hour_from_simple_dict(
    simple_dict: dict,
) -> weekdayDictOfListOfTradingHoursAnyDay:
    weekday_dict = dict(
        [
            (
                weekday_name,
                listOfTradingHoursAnyDay.from_simple_list(
                    simple_dict.get(weekday_name, [])
                ),
            )
            for weekday_name in list_of_weekday_names
        ]
    )

    return weekdayDictOfListOfTradingHoursAnyDay(weekday_dict)


def weekday_dict_of_trading_hours_from_simple_list(
    simple_list: list,
) -> weekdayDictOfListOfTradingHoursAnyDay:
    weekday_dict = dict(
        [
            (
                weekday_name,
                listOfTradingHoursAnyDay.from_simple_list(
                    simple_list  ## same opening times every day
                ),
            )
            for weekday_name in list_of_weekday_names
        ]
    )

    return weekdayDictOfListOfTradingHoursAnyDay(weekday_dict)
