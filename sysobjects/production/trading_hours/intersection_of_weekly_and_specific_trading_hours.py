from calendar import day_name

from sysobjects.production.trading_hours.trading_hours import (
    listOfTradingHours,
    tradingHours,
    split_trading_hours_across_two_weekdays,
)
from sysobjects.production.trading_hours.weekly_trading_hours_any_day import (
    weekdayDictOfListOfTradingHoursAnyDay,
    listOfTradingHoursAnyDay,
)


def intersection_of_any_weekly_and_list_of_normal_trading_hours(
    list_of_trading_hours: listOfTradingHours,
    weekly_any_trading_hours: weekdayDictOfListOfTradingHoursAnyDay,
) -> listOfTradingHours:

    list_of_intersecting_trading_hours = []
    for trading_hours in list_of_trading_hours:
        intersected_trading_hours = intersection_of_any_weekly_and_trading_hours(
            trading_hours=trading_hours,
            weekly_any_trading_hours=weekly_any_trading_hours,
        )
        list_of_intersecting_trading_hours = (
            list_of_intersecting_trading_hours + intersected_trading_hours
        )

    return listOfTradingHours(list_of_intersecting_trading_hours)


def intersection_of_any_weekly_and_trading_hours(
    trading_hours: tradingHours,
    weekly_any_trading_hours: weekdayDictOfListOfTradingHoursAnyDay,
) -> listOfTradingHours:

    trading_hours_open_weekday = trading_hours.opening_time.weekday()
    trading_hours_close_weekday = trading_hours.closing_time.weekday()

    if trading_hours_close_weekday != trading_hours_open_weekday:
        return intersection_of_any_weekly_and_trading_hours_spanning_days(
            trading_hours=trading_hours,
            weekly_any_trading_hours=weekly_any_trading_hours,
        )

    ## We know that the hours will be on the same day now
    name_of_day = day_name[trading_hours_open_weekday]
    trading_hours_for_weekday = weekly_any_trading_hours[name_of_day]
    intersected_hours = intersect_trading_hours_with_hours_for_weekday(
        trading_hours, trading_hours_for_weekday
    )

    return intersected_hours


def intersection_of_any_weekly_and_trading_hours_spanning_days(
    trading_hours: tradingHours,
    weekly_any_trading_hours: weekdayDictOfListOfTradingHoursAnyDay,
) -> listOfTradingHours:

    list_of_split_hours = split_trading_hours_across_two_weekdays(trading_hours)
    list_of_trading_hours = []
    for one_day_trading_hours in list_of_split_hours:
        list_of_trading_hours = (
            list_of_trading_hours
            + intersection_of_any_weekly_and_trading_hours(
                one_day_trading_hours, weekly_any_trading_hours
            )
        )

    return listOfTradingHours(list_of_trading_hours)


def intersect_trading_hours_with_hours_for_weekday(
    trading_hours: tradingHours, trading_hours_for_weekday: listOfTradingHoursAnyDay
) -> listOfTradingHours:

    ## at this point the open and close date will be the same
    opening_date = trading_hours.opening_time.date()
    list_of_weekday_trading_hours_with_this_date = trading_hours_for_weekday.add_date(
        opening_date
    )
    intersection = (
        list_of_weekday_trading_hours_with_this_date.intersect_with_trading_hours(
            trading_hours
        )
    )

    return intersection
