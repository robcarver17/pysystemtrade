"""
Various routines to do with dates
"""
from dataclasses import dataclass
from enum import Enum

import datetime
import time
import calendar
import pandas as pd
import numpy as np

from syscore.objects import missing_data, arg_not_supplied

"""
First some constants
"""

CALENDAR_DAYS_IN_YEAR = 365.25

BUSINESS_DAYS_IN_YEAR = 256.0
ROOT_BDAYS_INYEAR = BUSINESS_DAYS_IN_YEAR ** 0.5

WEEKS_IN_YEAR = CALENDAR_DAYS_IN_YEAR / 7.0
ROOT_WEEKS_IN_YEAR = WEEKS_IN_YEAR ** 0.5

MONTHS_IN_YEAR = 12.0
ROOT_MONTHS_IN_YEAR = MONTHS_IN_YEAR ** 0.5

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

MONTH_LIST = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

def get_date_from_period_and_end_date(period: str,
                                      end_date = arg_not_supplied) -> datetime.datetime:
    if end_date is arg_not_supplied:
        end_date = datetime.datetime.now()

    if period=="YTD":
        return calculate_starting_day_of_current_year(end_date)
    elif period=="MTD":
        return calculate_starting_day_of_current_month(end_date)
    elif period=="QTD":
        return calculate_starting_day_of_current_quarter(end_date)
    elif period=="TAX":
        return calculate_starting_day_of_current_uk_tax_year(end_date)

    offset_date =  _get_previous_date_from_period_with_char_number(period, end_date)
    return offset_date

def _get_previous_date_from_period_with_char_number(period: str,
                          end_date: datetime.datetime) -> datetime.datetime:

    type_of_offset = period[-1]
    try:
        number_offset = int(period[:1])
    except:
        raise Exception("Offset %s not in pattern numberLetter eg 7D for 7 days")

    if type_of_offset=="M":
        offset_date = end_date+pd.DateOffset(months=-number_offset)
    elif type_of_offset=="D":
        offset_date = end_date+pd.DateOffset(days = -number_offset)
    elif type_of_offset=="W":
        offset_date = end_date + pd.DateOffset(days=-number_offset*7)
    elif type_of_offset=="B":
        offset_date = end_date+pd.tseries.offsets.BDay(-number_offset)
    elif type_of_offset=="Y":
        offset_date = end_date+pd.DateOffset(years = -number_offset)
    else:
        raise Exception("Type of offset %s not recognised must be one of BDMYW" % type_of_offset)

    return offset_date

def calculate_starting_day_of_current_year(end_date) -> datetime.datetime:
    return datetime.datetime(year=end_date.year,
                             month=1,
                             day=1)

def calculate_starting_day_of_current_uk_tax_year(end_date: datetime.datetime) -> datetime.datetime:
    current_month = end_date.month
    current_day = end_date.day
    current_year = end_date.year
    if current_month<5 and current_day<6:
        return datetime.datetime(year=current_year-1, month=4, day=6)
    else:
        return datetime.datetime(year = current_year, month=4, day=6)

def calculate_starting_day_of_current_month(end_date) -> datetime.datetime:
    return datetime.datetime(year = end_date.year, month = end_date.month, day=1)

def calculate_starting_day_of_current_quarter(end_date):
    current_month = end_date.month
    current_quarter = int(np.ceil(current_month/3))
    start_month_of_quarter = ((current_quarter -1)*3)+1
    return datetime.datetime(year = end_date.year,
                             month = start_month_of_quarter,
                             day=1)



Frequency = Enum(
    "Frequency",
    "Unknown Year Month Week BDay Day Hour Minutes_15 Minutes_5 Minute Seconds_10 Second",
)
DAILY_PRICE_FREQ = Frequency.Day
BUSINESS_DAY_FREQ = Frequency.BDay
HOURLY_FREQ = Frequency.Hour

def from_config_frequency_pandas_resample(freq: Frequency) -> str:
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

    return resample_string


def from_frequency_to_times_per_year(freq: Frequency) -> float:
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

    return float(times_per_year)


def from_config_frequency_to_frequency(freq_as_str: str) -> Frequency:
    LOOKUP_TABLE = {
        "Y": Frequency.Year,
        "m": Frequency.Month,
        "W": Frequency.Week,
        "D": Frequency.Day,
        "H": Frequency.Hour,
        "15M": Frequency.Minutes_15,
        "5M": Frequency.Minutes_5,
        "M": Frequency.Minute,
        "10S": Frequency.Seconds_10,
        "S": Frequency.Second,
    }

    frequency = LOOKUP_TABLE.get(freq_as_str, missing_data)

    return frequency


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
        month_number = MONTH_LIST.index(contract_letter)
    except ValueError:
        raise Exception(
            "Contract letter %s is not a valid future month (must be one of %s)"
            % (contract_letter, str(MONTH_LIST))
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
    AssertionError
    >>> contract_month_from_number(13)
    AssertionError

    :param month_number: int
    :return: str
    """

    assert month_number > 0 and month_number < 13

    return MONTH_LIST[month_number - 1]


def get_datetime_from_datestring(datestring: str):
    """
    Translates a date which could be "20150305" or "201505" into a datetime


    :param datestring: Date to be processed
    :type days: str

    :returns: datetime.datetime

    >>> get_datetime_from_datestring('201503')
    datetime.datetime(2015, 3, 1, 0, 0)

    >>> get_datetime_from_datestring('20150300')
    datetime.datetime(2015, 3, 1, 0, 0)

    >>> get_datetime_from_datestring('20150305')
    datetime.datetime(2015, 3, 5, 0, 0)

    >>> get_datetime_from_datestring('2015031')
    Exception: 2015031 needs to be a string with 6 or 8 digits
    >>> get_datetime_from_datestring('2015013')
    Exception: 2015013 needs to be a string with 6 or 8 digits

    """

    # do string expiry calc
    if len(datestring) == 8:
        if datestring[6:8] == "00":
            return datetime.datetime.strptime(datestring, "%Y%m")
        else:
            return datetime.datetime.strptime(datestring, "%Y%m%d")
    if len(datestring) == 6:
        return datetime.datetime.strptime(datestring, "%Y%m")
    else:
        raise Exception("%s needs to be a string with 6 or 8 digits" % datestring)


class fit_dates_object(object):
    def __init__(self, fit_start, fit_end, period_start, period_end, no_data=False):
        setattr(self, "fit_start", fit_start)
        setattr(self, "fit_end", fit_end)
        setattr(self, "period_start", period_start)
        setattr(self, "period_end", period_end)
        setattr(self, "no_data", no_data)

    def __repr__(self):
        if self.no_data:
            return "Fit without data, use from %s to %s" % (
                self.period_start,
                self.period_end,
            )
        else:
            return "Fit from %s to %s, use in %s to %s" % (
                self.fit_start,
                self.fit_end,
                self.period_start,
                self.period_end,
            )


def time_matches(
    index_entry, closing_time=pd.DateOffset(hours=12, minutes=0, seconds=0)
):
    if (
        index_entry.hour == closing_time.hours
        and index_entry.minute == closing_time.minutes
        and index_entry.second == closing_time.seconds
    ):

        return True
    else:
        return False


"""
Convert date into a decimal, and back again
"""
LONG_DATE_FORMAT = "%Y%m%d%H%M%S.%f"
LONG_TIME_FORMAT = "%H%M%S.%f"
LONG_JUST_DATE_FORMAT = "%Y%m%d"
CONVERSION_FACTOR = 10000


def datetime_to_long(date_to_convert: datetime.datetime) -> int:
    as_str = date_to_convert.strftime(LONG_DATE_FORMAT)
    as_float = float(as_str)
    return int(as_float * CONVERSION_FACTOR)


def long_to_datetime(int_to_convert: int) -> datetime.datetime:
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


NOTIONAL_CLOSING_TIME = dict(hours=23, minutes=0, seconds=0)
NOTIONAL_CLOSING_TIME_AS_PD_OFFSET = pd.DateOffset(
    hours=NOTIONAL_CLOSING_TIME["hours"],
    minutes=NOTIONAL_CLOSING_TIME["minutes"],
    seconds=NOTIONAL_CLOSING_TIME["seconds"],
)


def adjust_timestamp_to_include_notional_close_and_time_offset(
    timestamp: datetime.datetime,
    actual_close: pd.DateOffset = NOTIONAL_CLOSING_TIME_AS_PD_OFFSET,
    original_close: pd.DateOffset = pd.DateOffset(hours=23, minutes=0, seconds=0),
    time_offset: pd.DateOffset = pd.DateOffset(hours=0),
) -> datetime.datetime:

    if timestamp.hour == 0 and timestamp.minute == 0 and timestamp.second == 0:
        new_datetime = timestamp.date() + actual_close
    elif time_matches(timestamp, original_close):
        new_datetime = timestamp.date() + actual_close
    else:
        new_datetime = timestamp + time_offset

    return new_datetime


def strip_timezone_fromdatetime(timestamp_with_tz_info) -> datetime.datetime:
    ts = timestamp_with_tz_info.timestamp()
    new_timestamp = datetime.datetime.fromtimestamp(ts)
    return new_timestamp


SHORT_DATE_PATTERN = "%m/%d %H:%M:%S"
MISSING_STRING_PATTERN = "     ???      "


def last_run_or_heartbeat_from_date_or_none(last_run_or_heartbeat: datetime.datetime):
    if last_run_or_heartbeat is missing_data or last_run_or_heartbeat is None:
        last_run_or_heartbeat = MISSING_STRING_PATTERN
    else:
        last_run_or_heartbeat = last_run_or_heartbeat.strftime(SHORT_DATE_PATTERN)

    return last_run_or_heartbeat


date_formatting = "%Y%m%d_%H%M%S"


def create_datetime_string(datetime_to_use: datetime = arg_not_supplied):
    if datetime_to_use is arg_not_supplied:
        datetime_to_use = datetime.datetime.now()

    datetime_marker = datetime_to_use.strftime(date_formatting)

    return datetime_marker


def from_marker_to_datetime(datetime_marker):
    return datetime.datetime.strptime(datetime_marker, date_formatting)


def two_weeks_ago():
    return n_days_ago(14)


def four_weeks_ago():
    return n_days_ago(28)


def n_days_ago(n_days: int, date_ref=arg_not_supplied):
    if date_ref is arg_not_supplied:
        date_ref = datetime.datetime.now()
    date_diff = datetime.timedelta(days=n_days)
    return date_ref - date_diff

### Opening times

@dataclass()
class openingTimes():
    opening_time: datetime.datetime
    closing_time: datetime.datetime
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


@dataclass()
class openingTimesAnyDay():
    opening_time: datetime.time
    closing_time: datetime.time


class listOfOpeningTimes(list):
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





def generate_equal_dates_within_year(
    year: int, number_of_dates: int, force_start_year_align: bool = False
) -> list:

    days_between_periods = int(CALENDAR_DAYS_IN_YEAR / float(number_of_dates))
    full_increment = datetime.timedelta(days=days_between_periods)
    start_of_year = datetime.datetime(year, 1, 1)

    if force_start_year_align:
        ## more realistic for most rolling calendars
        first_date = start_of_year
    else:
        half_period = int(days_between_periods / 2)
        half_period_increment = datetime.timedelta(days=half_period)
        first_date = start_of_year + half_period_increment

    all_dates = [
        first_date + full_increment * increment_size
        for increment_size in range(number_of_dates)
    ]

    return all_dates


def get_approx_vol_scalar_for_period(start_date:datetime.datetime,
                              end_date = datetime.datetime) -> float:
    time_between = end_date - start_date
    seconds_between= time_between.total_seconds()
    days_between = seconds_between / SECONDS_PER_DAY

    return days_between**.5


def calculate_start_and_end_dates(
        calendar_days_back = arg_not_supplied,
        end_date: datetime.datetime = arg_not_supplied,
        start_date: datetime.datetime = arg_not_supplied,
        start_period: str = arg_not_supplied,
        end_period: str = arg_not_supplied) -> tuple:

    ## DO THE END DATE FIRST
    ## First preference is to use period
    if end_period is arg_not_supplied:
        ## OK preference is to use passed date, if there was one
        if end_date is arg_not_supplied:
            end_date = datetime.datetime.now()
        else:
            # Use passed end date
            pass
    else:
        end_date = get_date_from_period_and_end_date(end_period)

    ## DO THE START DATE NEXT
    ## First preference is to use period, then calendar days, then passed date
    if start_period is arg_not_supplied:
        if calendar_days_back is arg_not_supplied:
            ## no period or calendar days, use passed date
            if start_date is arg_not_supplied:
                raise Exception("Have to specify one of calendar days back, start period or start date!")
            else:
                ## Use passed start date
                pass
        else:
            ## Calendar days
            start_date = n_days_ago(calendar_days_back, end_date)
    else:
        ## have a period
        start_date = get_date_from_period_and_end_date(start_period, end_date)

    return start_date, end_date

