"""
Various routines to do with dates
"""
from enum import Enum

import datetime
import time
import calendar
import numpy as np
import pandas as pd

from syscore.genutils import sign
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


Frequency = Enum('Frequency', 'Unknown Year Month Week BDay Day Hour Minutes_15 Minutes_5 Minute Seconds_10 Second')
DAILY_PRICE_FREQ = Frequency.Day
BUSINESS_DAY_FREQ = Frequency.BDay

def from_config_frequency_pandas_resample(freq: Frequency) -> str:
    LOOKUP_TABLE = {Frequency.BDay: 'B',
                    Frequency.Week: 'W',
                    Frequency.Month: 'M',
                    Frequency.Hour: 'H',
                    Frequency.Year: 'A',
                    Frequency.Day: 'D',
                    Frequency.Minutes_15: '15T',
                    Frequency.Minutes_5: '5T',
                    Frequency.Seconds_10: '10S',
                    Frequency.Second: 'S'}
    resample_string = LOOKUP_TABLE.get(freq, missing_data)

    return resample_string

def from_frequency_to_times_per_year(freq: Frequency) -> float:
    LOOKUP_TABLE = {Frequency.BDay: BUSINESS_DAYS_IN_YEAR,
                    Frequency.Week: WEEKS_IN_YEAR,
                    Frequency.Month: MONTHS_IN_YEAR,
                    Frequency.Hour: HOURS_PER_DAY * BUSINESS_DAYS_IN_YEAR,
                    Frequency.Year: 1,
                    Frequency.Day: CALENDAR_DAYS_IN_YEAR,
                    Frequency.Minutes_15: (MINUTES_PER_YEAR/15),
                    Frequency.Minutes_5: (MINUTES_PER_YEAR/5),
                    Frequency.Seconds_10: SECONDS_IN_YEAR/10,
                    Frequency.Second: SECONDS_IN_YEAR}
    times_per_year = LOOKUP_TABLE.get(freq, missing_data)

    return float(times_per_year)

def from_config_frequency_to_frequency(freq_as_str:str)-> Frequency:
    LOOKUP_TABLE = {'Y': Frequency.Year,
                    'm': Frequency.Month,
        'W': Frequency.Week,
        'D':Frequency.Day,
                        'H':Frequency.Hour,
                        '15M': Frequency.Minutes_15,
                        '5M': Frequency.Minutes_5,
                        'M': Frequency.Minute,
                        '10S': Frequency.Seconds_10,
                        'S': Frequency.Second}

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
        raise Exception("Contract letter %s is not a valid future month (must be one of %s)" %
                        (contract_letter, str(MONTH_LIST)))

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

    assert month_number>0 and month_number<13

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
        raise Exception(
            "%s needs to be a string with 6 or 8 digits" % datestring
        )




def _DEPRECATE_fraction_of_year_between_price_and_carry_expiries(carry_row: pd.Series,
                                                      floor_date_diff: float = 1/CALENDAR_DAYS_IN_YEAR) -> float:
    """
    Given a pandas row containing CARRY_CONTRACT and PRICE_CONTRACT, both of
    which represent dates

    Return the difference between the dates as a fraction

    Positive means PRICE BEFORE CARRY, negative means CARRY BEFORE PRICE

    :param carry_row: object with attributes CARRY_CONTRACT and PRICE_CONTRACT
    :type carry_row: pandas row, or something that quacks like it

    :param floor_date_diff: If date resolves to less than this, floor here (*default* 20)
    :type int

    :returns: float

    >>> import pandas as pd
    >>> carry_df = pd.DataFrame(dict(PRICE_CONTRACT =["20200601", "20200601", "20200601"],\
                                    CARRY_CONTRACT = ["20200303", "20200905", "20200603"]))
    >>> fraction_of_year_between_price_and_carry_expiries(carry_df.iloc[0])
    -0.2464065708418891
    >>> fraction_of_year_between_price_and_carry_expiries(carry_df.iloc[1])
    0.26283367556468173
    >>> fraction_of_year_between_price_and_carry_expiries(carry_df.iloc[2], floor_date_diff= 50)
    0.13689253935660506

    """
    fraction_of_year_between_expiries = _DEPRECATE_get_fraction_of_year_between_expiries(carry_row)
    if np.isnan(fraction_of_year_between_expiries):
        return np.nan

    fraction_of_year_between_expiries = _DEPRECATE_apply_floor_to_date_differential(fraction_of_year_between_expiries,
                                                             floor_date_diff=floor_date_diff)

    return fraction_of_year_between_expiries

def _DEPRECATE_get_fraction_of_year_between_expiries(carry_row) -> float:
    if carry_row.PRICE_CONTRACT == "" or carry_row.CARRY_CONTRACT == "":
        return np.nan

    carry_expiry =  _DEPRECATE_get_approx_year_as_number_from_date_as_string(carry_row.CARRY_CONTRACT)
    price_expiry = _DEPRECATE_get_approx_year_as_number_from_date_as_string(carry_row.PRICE_CONTRACT)
    fraction_of_year_between_expiries = carry_expiry - price_expiry

    return fraction_of_year_between_expiries

def _DEPRECATE_get_approx_year_as_number_from_date_as_string(date_string: str):
    ## Faster than using get_datetime_from_datestring, and approximate
    year = float(date_string[:4])
    month = float(date_string[5:])
    month_as_year_frac = month / 12.0

    year_from_zero = year + month_as_year_frac

    return year_from_zero

def _DEPRECATE_apply_floor_to_date_differential(fraction_of_year_between_expiries: float,
                                     floor_date_diff: float):
    if abs(fraction_of_year_between_expiries) < floor_date_diff:
        fraction_of_year_between_expiries = \
            sign(fraction_of_year_between_expiries) * floor_date_diff

    return fraction_of_year_between_expiries

class fit_dates_object(object):
    def __init__(
            self,
            fit_start,
            fit_end,
            period_start,
            period_end,
            no_data=False):
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


def generate_fitting_dates(data: pd.DataFrame, date_method: str, rollyears: int=20):
    """
    generate a list 4 tuples, one element for each year in the data
    each tuple contains [fit_start, fit_end, period_start, period_end] datetime objects
    the last period will be a 'stub' if we haven't got an exact number of years

    date_method can be one of 'in_sample', 'expanding', 'rolling'

    if 'rolling' then use rollyears variable
    """
    print("*** USE METHOD IN SYSQUANT INSTEAD**")
    if date_method not in ["in_sample", "rolling", "expanding"]:
        raise Exception(
            "don't recognise date_method %s should be one of in_sample, expanding, rolling" %
            date_method)

    if isinstance(data, list):
        start_date = min([dataitem.index[0] for dataitem in data])
        end_date = max([dataitem.index[-1] for dataitem in data])
    else:
        start_date = data.index[0]
        end_date = data.index[-1]

    # now generate the dates we use to fit
    if date_method == "in_sample":
        # single period
        return [fit_dates_object(start_date, end_date, start_date, end_date)]

    # generate list of dates, one year apart, including the final date
    yearstarts = list(
        pd.date_range(
            start_date,
            end_date,
            freq="12M")) + [end_date]

    # loop through each period
    periods = []
    for tidx in range(len(yearstarts))[1:-1]:
        # these are the dates we test in
        period_start = yearstarts[tidx]
        period_end = yearstarts[tidx + 1]

        # now generate the dates we use to fit
        if date_method == "expanding":
            fit_start = start_date
        elif date_method == "rolling":
            yearidx_to_use = max(0, tidx - rollyears)
            fit_start = yearstarts[yearidx_to_use]
        else:
            raise Exception(
                "don't recognise date_method %s should be one of in_sample, expanding, rolling" %
                date_method)

        if date_method in ["rolling", "expanding"]:
            fit_end = period_start
        else:
            raise Exception("don't recognise date_method %s " % date_method)

        periods.append(
            fit_dates_object(
                fit_start,
                fit_end,
                period_start,
                period_end))

    if date_method in ["rolling", "expanding"]:
        # add on a dummy date for the first year, when we have no data
        periods = [
            fit_dates_object(
                start_date, start_date, start_date, yearstarts[1], no_data=True
            )
        ] + periods

    return periods


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


def datetime_to_long(date_to_convert: datetime.datetime)-> int:
    as_str = date_to_convert.strftime(LONG_DATE_FORMAT)
    as_float = float(as_str)
    return int(as_float * CONVERSION_FACTOR)


def long_to_datetime(int_to_convert:int) -> datetime.datetime:
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
NOTIONAL_CLOSING_TIME_AS_PD_OFFSET = pd.DateOffset(hours = NOTIONAL_CLOSING_TIME['hours'],
                                                   minutes = NOTIONAL_CLOSING_TIME['minutes'],
                                                   seconds = NOTIONAL_CLOSING_TIME['seconds'])

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


def get_datetime_input(prompt:str, allow_default:bool=True, allow_no_arg:bool=False):
    invalid_input = True
    input_str = (
        prompt +
        ": Enter date and time in format %Y%-%m-%d eg '2020-05-30' OR '%Y-%m-%d %H:%M:%S' eg '2020-05-30 14:04:11'")
    if allow_default:
        input_str = input_str + " <RETURN for now>"
    if allow_no_arg:
        input_str = input_str + " <SPACE for no date>' "
    while invalid_input:
        ans = input(input_str)
        if ans == "" and allow_default:
            return datetime.datetime.now()
        if ans == " " and allow_no_arg:
            return None
        try:
            if len(ans) == 10:
                return_datetime = datetime.datetime.strptime(ans, "%Y-%m-%d")
            elif len(ans) == 19:
                return_datetime = datetime.datetime.strptime(ans, "%Y-%m-%d %H:%M:%S")
            else:
                # problems formatting will also raise value error
                raise ValueError
            return return_datetime

        except ValueError:
            print("%s is not a valid datetime string" % ans)
            continue



class tradingStartAndEndDateTimes(object):
    def __init__(self, hour_tuple):
        self._start_time = hour_tuple[0]
        self._end_time = hour_tuple[1]

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    def okay_to_trade_now(self) -> bool:
        datetime_now = datetime.datetime.now()
        if datetime_now >= self.start_time and datetime_now <= self.end_time:
            return True
        else:
            return False

    def hours_left_before_market_close(self)->float:
        if not self.okay_to_trade_now():
            # market closed
            return 0

        datetime_now = datetime.datetime.now()
        time_left = self.end_time - datetime_now
        seconds_left = time_left.total_seconds()
        hours_left = float(seconds_left) / SECONDS_PER_HOUR

        return hours_left


    def less_than_N_hours_left(self, N_hours: float = 1.0) -> bool:
        hours_left = self.hours_left_before_market_close()
        if hours_left<N_hours:
            return True
        else:
            return False

class manyTradingStartAndEndDateTimes(list):
    def __init__(self, list_of_trading_hours):
        """

        :param list_of_trading_hours: list of tuples, both datetime, first is start and second is end
        """

        list_of_start_and_end_objects = []
        for hour_tuple in list_of_trading_hours:
            this_period = tradingStartAndEndDateTimes(hour_tuple)
            list_of_start_and_end_objects.append(this_period)

        super().__init__(list_of_start_and_end_objects)


    def okay_to_trade_now(self):
        for check_period in self:
            if check_period.okay_to_trade_now():
                # okay to trade if it's okay to trade on some date
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


SHORT_DATE_PATTERN = "%m/%d %H:%M:%S"
MISSING_STRING_PATTERN = "     ???      "


def last_run_or_heartbeat_from_date_or_none(last_run_or_heartbeat: datetime.datetime):
    if last_run_or_heartbeat is missing_data or last_run_or_heartbeat is None:
        last_run_or_heartbeat = MISSING_STRING_PATTERN
    else:
        last_run_or_heartbeat = last_run_or_heartbeat.strftime(
            SHORT_DATE_PATTERN)

    return last_run_or_heartbeat


date_formatting = "%Y%m%d_%H%M%S"


def create_datetime_string(datetime_to_use):
    datetime_marker = datetime_to_use.strftime(date_formatting)

    return datetime_marker


def from_marker_to_datetime(datetime_marker):
    return datetime.datetime.strptime(datetime_marker, date_formatting)

def two_weeks_ago():
    return n_days_ago(14)

def n_days_ago(n_days: int, date_ref = arg_not_supplied):
    if date_ref is arg_not_supplied:
        date_ref = datetime.datetime.now()
    date_diff = datetime.timedelta(days = n_days)
    return date_ref - date_diff


def adjust_trading_hours_conservatively(trading_hours: list,
            conservative_times: tuple) -> list:

    new_trading_hours = [adjust_single_day_conservatively(single_days_hours,
                                                          conservative_times)
                         for single_days_hours in trading_hours]

    return new_trading_hours

def adjust_single_day_conservatively(single_days_hours: tuple,
                                     conservative_times: tuple) -> tuple:

    adjusted_start_datetime = adjust_start_time_conservatively(single_days_hours[0],
                                                               conservative_times[0])
    adjusted_end_datetime = adjust_end_time_conservatively(single_days_hours[1],
                                                           conservative_times[1])

    return (adjusted_start_datetime, adjusted_end_datetime)

def adjust_start_time_conservatively(start_datetime: datetime.datetime,
                                     start_conservative: datetime.time) -> datetime.datetime:

    start_conservative_datetime = adjust_date_conservatively(start_datetime,
                                                             start_conservative)
    return max(start_datetime, start_conservative_datetime)

def adjust_end_time_conservatively(end_datetime: datetime.datetime,
                                     end_conservative: datetime.time) -> datetime.datetime:

    end_conservative_datetime = adjust_date_conservatively(end_datetime,
                                                             end_conservative)
    return min(end_datetime, end_conservative_datetime)


def adjust_date_conservatively(datetime_to_be_adjusted: datetime.datetime,
                               conservative_time: datetime.time) -> datetime.datetime:

    return datetime.datetime.combine(datetime_to_be_adjusted.date(), conservative_time)
