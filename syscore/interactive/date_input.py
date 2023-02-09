import datetime
from typing import Tuple, Union

from syscore.dateutils import (
    n_days_ago,
    calculate_start_and_end_dates,
    get_date_from_period_and_end_date,
)
from syscore.constants import arg_not_supplied


def get_report_dates() -> Tuple[datetime.datetime, datetime.datetime]:

    end_date = arg_not_supplied
    start_date = arg_not_supplied
    start_period = arg_not_supplied
    end_period = arg_not_supplied

    input_end_date = get_datetime_input(
        "End date for report?\n",
        allow_default_datetime_of_now=True,
        allow_calendar_days=True,
        allow_period=True,
    )

    if type(input_end_date) is int:
        ## calendar days
        end_date = n_days_ago(input_end_date, datetime.datetime.now())
    elif type(input_end_date) is str:
        ## period
        end_period = input_end_date
    elif type(input_end_date) is datetime.datetime:
        end_date = input_end_date
    else:
        raise Exception("Don't recognise %s" % str(input_end_date))

    input_start_date = get_datetime_input(
        "Start date for report? \n",
        allow_default_datetime_of_now=False,
        allow_calendar_days=True,
        allow_period=True,
    )

    if type(input_start_date) is int:
        ## calendar days
        start_date = n_days_ago(input_start_date, end_date)
    elif type(input_start_date) is str:
        ## period
        start_period = input_start_date
    elif type(input_start_date) is datetime.datetime:
        start_date = input_start_date
    else:
        raise Exception("Don't recognise %s" % str(input_start_date))

    start_date, end_date = calculate_start_and_end_dates(
        calendar_days_back=arg_not_supplied,
        end_date=end_date,
        start_date=start_date,
        start_period=start_period,
        end_period=end_period,
    )

    return start_date, end_date


INVALID_DATETIME = object()


def get_datetime_input(
    prompt: str,
    allow_default_datetime_of_now: bool = True,
    allow_calendar_days: bool = False,
    allow_period: bool = False,
) -> Union[str, datetime.datetime, int]:

    input_str = _create_input_string_for_datetime_input(
        prompt=prompt,
        allow_default_datetime_of_now=allow_default_datetime_of_now,
        allow_period=allow_period,
        allow_calendar_days=allow_calendar_days,
    )
    invalid_input = True
    while invalid_input:
        ans = _get_input_for_datetime_prompt(
            input_str=input_str,
            allow_period=allow_period,
            allow_calendar_days=allow_calendar_days,
            allow_default_datetime_of_now=allow_default_datetime_of_now,
        )
        if ans is INVALID_DATETIME:
            continue
        else:
            break

    return ans


LONG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
SHORT_DATETIME_FORMAT = "%Y-%m-%d"
LONG_EXAMPLE = datetime.datetime.strftime(datetime.datetime.now(), LONG_DATETIME_FORMAT)
SHORT_EXAMPLE = datetime.datetime.strftime(
    datetime.datetime.now(), SHORT_DATETIME_FORMAT
)


def _create_input_string_for_datetime_input(
    prompt: str,
    allow_default_datetime_of_now: bool = True,
    allow_calendar_days: bool = False,
    allow_period: bool = False,
) -> str:
    input_str = (
        prompt
        + ": Enter date and time in format %s eg '%s' OR '%s' eg '%s'"
        % (SHORT_DATETIME_FORMAT, SHORT_EXAMPLE, LONG_DATETIME_FORMAT, LONG_EXAMPLE)
    )
    if allow_calendar_days:
        input_str = input_str + "\n OR [Enter an integer to go back N calendar days]"
    if allow_period:
        input_str = input_str + "OR [Enter a string for period, eg 'YTD', '3M', '2B']"
    if allow_default_datetime_of_now:
        input_str = input_str + "OR <RETURN for now>"

    return input_str


def _get_input_for_datetime_prompt(
    input_str: str,
    allow_default_datetime_of_now: bool = True,
    allow_calendar_days: bool = False,
    allow_period: bool = False,
):
    ans = input(input_str)
    if ans == "" and allow_default_datetime_of_now:
        return datetime.datetime.now()

    if allow_period:
        try:
            _NOT_USED = get_date_from_period_and_end_date(ans)
            ## all good, return as string
            return ans
        except:
            pass

    if allow_calendar_days:
        try:
            ans_as_int = int(ans)
            return ans_as_int
        except:
            pass

    try:
        ans_as_datetime = _resolve_datetime_input_str(ans)
        return ans_as_datetime
    except:
        pass

    print("%s is not any valid input string" % ans)

    return INVALID_DATETIME


def _resolve_datetime_input_str(ans) -> datetime.datetime:
    if len(ans) == len(SHORT_EXAMPLE):
        return_datetime = datetime.datetime.strptime(ans, SHORT_DATETIME_FORMAT)
    elif len(ans) == len(LONG_EXAMPLE):
        return_datetime = datetime.datetime.strptime(ans, LONG_DATETIME_FORMAT)
    else:
        # problems formatting will also raise value error
        raise ValueError

    return return_datetime
