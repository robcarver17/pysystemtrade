"""
Various routines to do with dates
"""

import calendar
import datetime
import time

from enum import Enum
from typing import List, Union, Tuple

import pandas as pd
import numpy as np

from syscore.exceptions import missingData
from syscore.constants import missing_data, arg_not_supplied

"""

 GENERAL CONSTANTS

"""

CALENDAR_DAYS_IN_YEAR = 365.25

BUSINESS_DAYS_IN_YEAR = 256.0
ROOT_BDAYS_INYEAR = BUSINESS_DAYS_IN_YEAR**0.5

WEEKS_IN_YEAR = CALENDAR_DAYS_IN_YEAR / 7.0
ROOT_WEEKS_IN_YEAR = WEEKS_IN_YEAR**0.5

MONTHS_IN_YEAR = 12.0
ROOT_MONTHS_IN_YEAR = MONTHS_IN_YEAR**0.5

APPROX_DAYS_IN_MONTH = CALENDAR_DAYS_IN_YEAR / MONTHS_IN_YEAR

ARBITRARY_START = datetime.datetime(1900, 1, 1)

HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = MINUTES_PER_HOUR * SECONDS_PER_MINUTE
SECONDS_PER_DAY = HOURS_PER_DAY * SECONDS_PER_HOUR

SECONDS_IN_YEAR = CALENDAR_DAYS_IN_YEAR * SECONDS_PER_DAY
MINUTES_PER_YEAR = CALENDAR_DAYS_IN_YEAR * HOURS_PER_DAY * MINUTES_PER_HOUR
UNIXTIME_CONVERTER = 1e9

UNIXTIME_IN_YEAR = UNIXTIME_CONVERTER * SECONDS_IN_YEAR

"""
 
 RELATIVE TIME REFERENCING

"""


def calculate_start_and_end_dates(
    calendar_days_back: int = arg_not_supplied,
    end_date: datetime.datetime = arg_not_supplied,
    start_date: datetime.datetime = arg_not_supplied,
    start_period: str = arg_not_supplied,
    end_period: str = arg_not_supplied,
) -> Tuple[datetime.datetime, datetime.datetime]:

    resolved_end_date = _resolve_end_date_given_period_and_explicit_end_date(
        end_date=end_date, end_period=end_period
    )
    resolved_start_date = _resolve_start_date_given_end_date_calendar_days_and_period(
        resolved_end_date=resolved_end_date,
        start_date=start_date,
        start_period=start_period,
        calendar_days_back=calendar_days_back,
    )

    return resolved_start_date, resolved_end_date


def _resolve_end_date_given_period_and_explicit_end_date(
    end_date: datetime.datetime = arg_not_supplied,
    end_period: str = arg_not_supplied,
) -> datetime.datetime:
    """
    >>> _resolve_end_date_given_period_and_explicit_end_date(end_date=datetime.datetime(2022,1,1))
    datetime.datetime(2022, 1, 1, 0, 0)
    >>> _resolve_end_date_given_period_and_explicit_end_date(end_period="1M", end_date=datetime.datetime(2022,4,1))
    datetime.datetime(2022, 3, 1, 0, 0)

    """
    ## Preference: Use period, use explicit end date, use now()
    ## First preference is to use period
    if end_period is arg_not_supplied:
        ## OK preference is to use passed date, if there was one
        if end_date is arg_not_supplied:
            ## Nothing passed use now
            return datetime.datetime.now()
        else:
            # Use explicit passed end date
            return end_date
    else:
        # use period string (date will probably not have an effect except when debugging)
        return get_date_from_period_and_end_date(end_period, end_date=end_date)


def _resolve_start_date_given_end_date_calendar_days_and_period(
    resolved_end_date: datetime.datetime,
    calendar_days_back: int = arg_not_supplied,
    start_date: datetime.datetime = arg_not_supplied,
    start_period: str = arg_not_supplied,
) -> datetime.datetime:
    """
    >>> _resolve_start_date_given_end_date_calendar_days_and_period(resolved_end_date = datetime.datetime(2023,1,1), calendar_days_back = 5, start_date = datetime.datetime(2022,1,1), start_period="2Y")
    datetime.datetime(2021, 1, 1, 0, 0)
    >>> _resolve_start_date_given_end_date_calendar_days_and_period(resolved_end_date = datetime.datetime(2023,1,1), calendar_days_back = 5, start_date = datetime.datetime(2022,1,1))
    datetime.datetime(2022, 1, 1, 0, 0)
    >>> _resolve_start_date_given_end_date_calendar_days_and_period(resolved_end_date = datetime.datetime(2023,1,7), calendar_days_back = 5)
    datetime.datetime(2023, 1, 2, 0, 0)
    >>> _resolve_start_date_given_end_date_calendar_days_and_period(resolved_end_date = datetime.datetime(2023,1,7))
    Exception: Have to specify one of calendar days back, start period or start date!

    """
    ## First preference is to use period, then passed date, then calendar days
    if start_period is arg_not_supplied:
        if start_date is arg_not_supplied:
            ## no period or calendar days, use passed date
            if calendar_days_back is arg_not_supplied:
                raise Exception(
                    "Have to specify one of calendar days back, start period or start date!"
                )
            else:
                ## Have calendar days
                return n_days_ago(calendar_days_back, resolved_end_date)
        else:
            ## Use passed start date
            return start_date
    else:
        ## have a start period, use that
        return get_date_from_period_and_end_date(start_period, resolved_end_date)


def n_days_ago(n_days: int, end_date=arg_not_supplied) -> datetime.datetime:
    """
    Calculates date N days ago

    >>> n_days_ago(16, datetime.datetime(2023,4,15,12,15))
    datetime.datetime(2023, 3, 30, 12, 15)

    """

    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()

    period = "%dD" % n_days

    return calculate_previous_date_from_period_with_char_number(period, end_date)


def get_date_from_period_and_end_date(
    period: str, end_date=arg_not_supplied
) -> datetime.datetime:
    """
    Calculates date according to offset

    >>> get_date_from_period_and_end_date('YTD', datetime.date(2023,5,15))
    datetime.datetime(2023, 1, 1, 0, 0)
    >>> get_date_from_period_and_end_date('MTD', datetime.date(2023,5,15))
    datetime.datetime(2023, 5, 1, 0, 0)
    >>> get_date_from_period_and_end_date('QTD', datetime.date(2023,5,15))
    datetime.datetime(2023, 4, 1, 0, 0)
    >>> get_date_from_period_and_end_date('TAX', datetime.datetime(2023,5,15))
    datetime.datetime(2023, 4, 6, 0, 0)
    >>> get_date_from_period_and_end_date('2M', datetime.datetime(2023,5,15,12,15))
    datetime.datetime(2023, 3, 15, 12, 15)

    """
    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()

    if period == "YTD":
        return calculate_starting_day_of_current_year(end_date)
    elif period == "MTD":
        return calculate_starting_day_of_current_month(end_date)
    elif period == "QTD":
        return calculate_starting_day_of_current_quarter(end_date)
    elif period == "TAX":
        return calculate_starting_day_of_current_uk_tax_year(end_date)

    offset_date = calculate_previous_date_from_period_with_char_number(period, end_date)

    return offset_date


def calculate_previous_date_from_period_with_char_number(
    period: str, end_date: datetime.datetime
) -> datetime.datetime:
    """
    Calculates date according to string offset

    >>> calculate_previous_date_from_period_with_char_number('1M', datetime.datetime(2023,4,15,12,15))
    datetime.datetime(2023, 3, 15, 12, 15)
    >>> calculate_previous_date_from_period_with_char_number('16D', datetime.datetime(2023,4,15,12,15))
    datetime.datetime(2023, 3, 30, 12, 15)
    >>> calculate_previous_date_from_period_with_char_number('3W', datetime.datetime(2023,4,28,12,15))
    datetime.datetime(2023, 4, 7, 12, 15)
    >>> calculate_previous_date_from_period_with_char_number('6B', datetime.datetime(2023,4,15,12,15))
    datetime.datetime(2023, 4, 7, 12, 15)
    >>> calculate_previous_date_from_period_with_char_number('5Y', datetime.datetime(2023,4,15,12,15))
    datetime.datetime(2018, 4, 15, 12, 15)

    """

    type_of_offset = period[-1]
    try:
        number_offset = int(period[:-1])
    except:
        raise Exception("Offset %s not in pattern numberLetter eg 7D for 7 days")

    if type_of_offset == "M":
        offset_date = end_date + pd.DateOffset(months=-number_offset)
    elif type_of_offset == "D":
        offset_date = end_date + pd.DateOffset(days=-number_offset)
    elif type_of_offset == "W":
        offset_date = end_date + pd.DateOffset(days=-number_offset * 7)
    elif type_of_offset == "B":
        offset_date = end_date + pd.tseries.offsets.BDay(-number_offset)
    elif type_of_offset == "Y":
        offset_date = end_date + pd.DateOffset(years=-number_offset)
    else:
        raise Exception(
            "Type of offset %s not recognised must be one of BDMYW" % type_of_offset
        )

    return offset_date.to_pydatetime()


def calculate_starting_day_of_current_year(
    end_date: datetime.datetime,
) -> datetime.datetime:
    """
    Calculates date according to offset

    >>> calculate_starting_day_of_current_year(datetime.date(2023,5,15))
    datetime.datetime(2023, 1, 1, 0, 0)
    """
    return datetime.datetime(year=end_date.year, month=1, day=1)


def calculate_starting_day_of_current_uk_tax_year(
    end_date: datetime.datetime,
) -> datetime.datetime:
    """
    Calculates date according to offset

    >>> calculate_starting_day_of_current_uk_tax_year(datetime.date(2023,5,15))
    datetime.datetime(2023, 4, 6, 0, 0)
    >>> calculate_starting_day_of_current_uk_tax_year(datetime.date(2023,4,1))
    datetime.datetime(2022, 4, 6, 0, 0)
    """

    current_month = end_date.month
    current_day = end_date.day
    current_year = end_date.year
    if current_month < 5 and current_day < 6:
        return datetime.datetime(year=current_year - 1, month=4, day=6)
    else:
        return datetime.datetime(year=current_year, month=4, day=6)


def calculate_starting_day_of_current_month(
    end_date: datetime.datetime,
) -> datetime.datetime:
    return datetime.datetime(year=end_date.year, month=end_date.month, day=1)


def calculate_starting_day_of_current_quarter(
    end_date: datetime.datetime,
) -> datetime.datetime:
    current_month = end_date.month
    current_quarter = int(np.ceil(current_month / 3))
    start_month_of_quarter = ((current_quarter - 1) * 3) + 1
    return datetime.datetime(year=end_date.year, month=start_month_of_quarter, day=1)


MIDNIGHT = datetime.time(0, 0)
ONE_SECOND_BEFORE_MIDNIGHT = datetime.time(23, 59, 59)


def preceeding_midnight_of_datetime(
    some_datetime: datetime.datetime,
) -> datetime.datetime:
    """
    >>> preceeding_midnight_of_datetime(datetime.datetime(2022,1,1,15,12))
    datetime.datetime(2022, 1, 1, 0, 0)
    """
    return datetime.datetime.combine(some_datetime.date(), MIDNIGHT)


def preceeding_midnight_of_date(some_date: datetime.date) -> datetime.datetime:
    """
    >>> preceeding_midnight_of_date(datetime.date(2022,1,1))
    datetime.datetime(2022, 1, 1, 0, 0)
    """
    return datetime.datetime.combine(some_date, MIDNIGHT)


def following_one_second_before_midnight_of_datetime(
    some_datetime: datetime.datetime,
) -> datetime.datetime:
    """
    >>> following_one_second_before_midnight_of_datetime(datetime.datetime(2022,1,1,15,12))
    datetime.datetime(2022, 1, 1, 23, 59, 59)
    """
    return datetime.datetime.combine(some_datetime.date(), ONE_SECOND_BEFORE_MIDNIGHT)


def following_one_second_before_midnight_of_date(
    some_date: datetime.date,
) -> datetime.datetime:
    """
    >>> following_one_second_before_midnight_of_date(datetime.datetime(2022,1,1,15,12))
    datetime.datetime(2022, 1, 1, 23, 59, 59)
    """
    return following_one_second_before_midnight_of_datetime(
        preceeding_midnight_of_date(some_date)
    )


"""

    FREQUENCIES

"""

Frequency = Enum(
    "Frequency",
    "Unknown Year Month Week BDay Day Hour Minutes_15 Minutes_5 Minute Seconds_10 Second Mixed",
)
DAILY_PRICE_FREQ = Frequency.Day
BUSINESS_DAY_FREQ = Frequency.BDay
HOURLY_FREQ = Frequency.Hour

MIXED_FREQ = Frequency.Mixed


def from_config_frequency_pandas_resample(freq: Frequency) -> str:
    """
    Translate between my frequencies and pandas frequencies

    >>> from_config_frequency_pandas_resample(BUSINESS_DAY_FREQ)
    'B'
    """

    LOOKUP_TABLE = {
        Frequency.BDay: "B",
        Frequency.Week: "W",
        Frequency.Month: "M",
        Frequency.Hour: "H",
        Frequency.Year: "A",
        Frequency.Day: "D",
        Frequency.Minutes_15: "15T",
        Frequency.Minutes_5: "5T",
        Frequency.Seconds_10: "10S",
        Frequency.Second: "S",
    }
    resample_string = LOOKUP_TABLE.get(freq, missing_data)

    if resample_string is missing_data:
        raise missingData("Resample frequency %s is not supported" % freq)

    return resample_string


def from_frequency_to_times_per_year(freq: Frequency) -> float:
    """
    Times a year that a frequency corresponds to

    >>> from_frequency_to_times_per_year(BUSINESS_DAY_FREQ)
    256.0
    """

    LOOKUP_TABLE = {
        Frequency.BDay: BUSINESS_DAYS_IN_YEAR,
        Frequency.Week: WEEKS_IN_YEAR,
        Frequency.Month: MONTHS_IN_YEAR,
        Frequency.Hour: HOURS_PER_DAY * BUSINESS_DAYS_IN_YEAR,
        Frequency.Year: 1,
        Frequency.Day: CALENDAR_DAYS_IN_YEAR,
        Frequency.Minutes_15: (MINUTES_PER_YEAR / 15),
        Frequency.Minutes_5: (MINUTES_PER_YEAR / 5),
        Frequency.Seconds_10: SECONDS_IN_YEAR / 10,
        Frequency.Second: SECONDS_IN_YEAR,
    }
    times_per_year = LOOKUP_TABLE.get(freq, missing_data)

    if times_per_year is missing_data:
        raise missingData("Frequency %s is not supported" % freq)

    return float(times_per_year)


def from_config_frequency_to_frequency(freq_as_str: str) -> Frequency:
    """
    Translate between configured letter frequencies and my frequencies

    >>> from_config_frequency_to_frequency('B')
    <Frequency.BDay: 5>
    """
    LOOKUP_TABLE = {
        "Y": Frequency.Year,
        "m": Frequency.Month,
        "W": Frequency.Week,
        "B": Frequency.BDay,
        "D": Frequency.Day,
        "H": Frequency.Hour,
        "15M": Frequency.Minutes_15,
        "5M": Frequency.Minutes_5,
        "M": Frequency.Minute,
        "10S": Frequency.Seconds_10,
        "S": Frequency.Second,
    }

    frequency = LOOKUP_TABLE.get(freq_as_str, missing_data)

    if frequency is missing_data:
        raise missingData("Frequency %s is not supported" % freq_as_str)

    return frequency


"""

    FUTURES MONTHS

"""

FUTURES_MONTH_LIST = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]


def month_from_contract_letter(contract_letter: str) -> int:
    """
    Returns month number (1 is January) from contract letter
    >>> month_from_contract_letter("F")
    1
    >>> month_from_contract_letter("Z")
    12
    >>> month_from_contract_letter("A")
    Exception: Contract letter A is not a valid future month (must be one of ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'])

    """

    try:
        month_number = FUTURES_MONTH_LIST.index(contract_letter)
    except ValueError:
        raise Exception(
            "Contract letter %s is not a valid future month (must be one of %s)"
            % (contract_letter, str(FUTURES_MONTH_LIST))
        )

    return month_number + 1


def contract_month_from_number(month_number: int) -> str:
    """
    Returns standard month letters used in futures land

    >>> contract_month_from_number(1)
    'F'
    >>> contract_month_from_number(12)
    'Z'
    >>> contract_month_from_number(0)
    Exception: Months have to be between 1 and 12
    >>> contract_month_from_number(13)
    Exception: Months have to be between 1 and 12

    :param month_number: int
    :return: str
    """

    try:
        assert month_number > 0 and month_number < 13
    except:
        raise Exception("Months have to be between 1 and 12")

    return FUTURES_MONTH_LIST[month_number - 1]


"""

     DATE / STRING / DECIMAL CONVERSIONS

"""

"""
Convert date into a decimal, and back again
"""
LONG_DATE_FORMAT = "%Y%m%d%H%M%S.%f"
CONVERSION_FACTOR = 10000


def datetime_to_long(date_to_convert: datetime.datetime) -> int:
    """
    Translate a datetime into a long integer

    >>> datetime_to_long(datetime.datetime(2023,1,15,6,32,7))
    202301150632070016
    """

    as_str = date_to_convert.strftime(LONG_DATE_FORMAT)
    as_float = float(as_str)
    return int(as_float * CONVERSION_FACTOR)


def long_to_datetime(int_to_convert: int) -> datetime.datetime:
    """
    Translate an integer into a datetime.datetime

    >>> long_to_datetime(202301150632070016)
    datetime.datetime(2023, 1, 15, 6, 32, 7)
    """

    as_float = float(int_to_convert) / CONVERSION_FACTOR
    str_to_convert = "%.6f" % as_float

    # have to do this because of leap seconds
    time_string, dot, microseconds = str_to_convert.partition(".")
    utc_time_tuple = time.strptime(str_to_convert, LONG_DATE_FORMAT)
    as_datetime = datetime.datetime(1970, 1, 1) + datetime.timedelta(
        seconds=calendar.timegm(utc_time_tuple)
    )
    as_datetime = as_datetime.replace(
        microsecond=datetime.datetime.strptime(microseconds, "%f").microsecond
    )

    return as_datetime


### SHORT DATES

SHORT_DATE_PATTERN = "%m/%d %H:%M:%S"
MISSING_STRING_PATTERN = "     ???      "


def date_as_short_pattern_or_question_if_missing(
    last_run_or_heartbeat: datetime.datetime,
) -> str:
    """
    Check time matches at one second resolution (good enough)

    >>> date_as_short_pattern_or_question_if_missing(datetime.datetime(2023, 1, 15, 6, 32))
    '01/15 06:32:00'
    >>> date_as_short_pattern_or_question_if_missing(106)
    '     ???      '
    """
    if isinstance(last_run_or_heartbeat, datetime.datetime):
        last_run_or_heartbeat = last_run_or_heartbeat.strftime(SHORT_DATE_PATTERN)
    else:
        last_run_or_heartbeat = MISSING_STRING_PATTERN

    return last_run_or_heartbeat


## MARKER DATES

MARKER_DATE_FORMAT = "%Y%m%d_%H%M%S"


def create_datetime_marker_string(datetime_to_use: datetime = arg_not_supplied) -> str:
    if datetime_to_use is arg_not_supplied:
        datetime_to_use = datetime.datetime.now()

    datetime_marker = datetime_to_use.strftime(MARKER_DATE_FORMAT)

    return datetime_marker


def from_marker_string_to_datetime(datetime_marker: str) -> datetime.datetime:
    return datetime.datetime.strptime(datetime_marker, MARKER_DATE_FORMAT)


## TIMES


def time_to_string(time: datetime.time):
    return time.strftime("%H:%M")


def time_from_string(time_string: str):
    split_string = time_string.split(":")

    return datetime.time(int(split_string[0]), int(split_string[1]))


"""

 CLOSING TIMES

"""

NOTIONAL_CLOSING_TIME_AS_PD_OFFSET = pd.DateOffset(
    hours=23,
    minutes=0,
    seconds=0,
)

MIDNIGHT_TIME_AS_PD_OFFSET = pd.DateOffset(
    hours=0,
    minutes=0,
    seconds=0,
)


def replace_midnight_with_notional_closing_time(
    timestamp: Union[datetime.datetime, datetime.date],
    notional_closing_time: pd.DateOffset = NOTIONAL_CLOSING_TIME_AS_PD_OFFSET,
) -> pd.Timestamp:
    """
    Replaces midnight with a notional closing time

    >>> replace_midnight_with_notional_closing_time(datetime.datetime(2023, 1, 15, 6, 32))
    Timestamp('2023-01-15 06:32:00')
    >>> replace_midnight_with_notional_closing_time(datetime.datetime(2023, 1, 15, 0, 0))
    Timestamp('2023-01-15 23:00:00')
    >>> replace_midnight_with_notional_closing_time(datetime.date(2023, 1, 15))
    Timestamp('2023-01-15 23:00:00')
    """
    if type(timestamp) is datetime.date:
        return timestamp + notional_closing_time
    elif check_time_matches_closing_time_to_second(
        timestamp, MIDNIGHT_TIME_AS_PD_OFFSET
    ):
        return timestamp.date() + notional_closing_time
    else:
        return pd.to_datetime(timestamp)


def check_time_matches_closing_time_to_second(
    index_entry: datetime.datetime,
    closing_time: pd.DateOffset = NOTIONAL_CLOSING_TIME_AS_PD_OFFSET,
) -> bool:
    """
    Check time matches at one second resolution (good enough)

    >>> check_time_matches_closing_time_to_second(datetime.datetime(2023, 1, 15, 6, 32))
    False
    >>> check_time_matches_closing_time_to_second(datetime.datetime(2023, 1, 15, 23, 0))
    True
    """

    if (
        index_entry.hour == closing_time.hours
        and index_entry.minute == closing_time.minutes
        and index_entry.second == closing_time.seconds
    ):

        return True
    else:
        return False


def strip_timezone_fromdatetime(timestamp_with_tz_info) -> datetime.datetime:
    ts = timestamp_with_tz_info.timestamp()
    new_timestamp = datetime.datetime.fromtimestamp(ts)
    return new_timestamp


"""
    
    EQUAL DATES WITHIN A YEAR

"""


def generate_equal_dates_within_year(
    year: int, number_of_dates: int, force_start_year_align: bool = False
) -> List[datetime.datetime]:

    """
    Generate equally spaced datetimes within a given year
    >>> generate_equal_dates_within_year(2022,3)
    [datetime.datetime(2022, 3, 2, 0, 0), datetime.datetime(2022, 7, 1, 0, 0), datetime.datetime(2022, 10, 30, 0, 0)]
    >>> generate_equal_dates_within_year(2022,1)
    [datetime.datetime(2022, 7, 2, 0, 0)]
    >>> generate_equal_dates_within_year(2021,2, force_start_year_align=True)
    [datetime.datetime(2021, 1, 1, 0, 0), datetime.datetime(2021, 7, 2, 0, 0)]
    """

    days_between_periods = int(CALENDAR_DAYS_IN_YEAR / float(number_of_dates))
    first_date = _calculate_first_date_for_equal_dates(
        year=year,
        days_between_periods=days_between_periods,
        force_start_year_align=force_start_year_align,
    )
    delta_for_each_period = datetime.timedelta(days=days_between_periods)

    all_dates = [
        first_date + (delta_for_each_period * period_count)
        for period_count in range(number_of_dates)
    ]

    return all_dates


def _calculate_first_date_for_equal_dates(
    year: int, days_between_periods: int, force_start_year_align: bool = False
) -> datetime.datetime:

    start_of_year = datetime.datetime(year, 1, 1)

    if force_start_year_align:
        ## more realistic for most rolling calendars
        first_date = start_of_year
    else:
        half_period = int(days_between_periods / 2)
        half_period_increment = datetime.timedelta(days=half_period)
        first_date = start_of_year + half_period_increment

    return first_date


"""

    VOL SCALING

"""


def get_approx_vol_scalar_versus_daily_vol_for_period(
    start_date: datetime.datetime, end_date=datetime.datetime
) -> float:
    time_between = end_date - start_date
    seconds_between = time_between.total_seconds()
    days_between = seconds_between / SECONDS_PER_DAY

    return days_between**0.5
