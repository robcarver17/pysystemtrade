import datetime
import yaml
from ib_insync import ContractDetails as ibContractDetails

from sysobjects.production.trading_hours import openingTimes, openingTimesAnyDay, listOfOpeningTimes
from syscore.fileutils import get_filename_for_package
from sysdata.config.production_config import get_production_config
from sysdata.production.trading_hours import read_trading_hours

IB_FUTURES_CONFIG_FILE = get_filename_for_package("sysbrokers.IB.ib_config_trading_hours.yaml")

def get_saved_trading_hours():
    return read_trading_hours(IB_FUTURES_CONFIG_FILE)



def get_trading_hours(ib_contract_details: ibContractDetails) -> listOfOpeningTimes:
    try:
        time_zone_id = ib_contract_details.timeZoneId
        time_zone_adjustment = get_time_difference(time_zone_id)
        one_off_adjustment = one_off_adjustments(ib_contract_details.contract.symbol)

        trading_hours_string = ib_contract_details.tradingHours
        list_of_open_times = parse_trading_hours_string(
            trading_hours_string,
            adjustment_hours=time_zone_adjustment,
            one_off_adjustment=one_off_adjustment,
        )
    except Exception as e:
        raise e

    return list_of_open_times


NO_ADJUSTMENTS = 0, 0
CLOSED_ALL_DAY = object()

def parse_trading_hours_string(
    trading_hours_string: str,
    adjustment_hours: int = 0,
    one_off_adjustment: tuple = NO_ADJUSTMENTS,
    ) -> listOfOpeningTimes:

    day_by_day = trading_hours_string.split(";")
    list_of_open_times = [
        parse_trading_for_day(
            string_for_day,
            adjustment_hours=adjustment_hours,
            one_off_adjustment=one_off_adjustment,
        )
        for string_for_day in day_by_day
    ]

    list_of_open_times = [
        open_time for open_time in list_of_open_times if open_time is not CLOSED_ALL_DAY
    ]

    list_of_open_times = listOfOpeningTimes(list_of_open_times)

    return list_of_open_times


def parse_trading_for_day(
    string_for_day: str,
    adjustment_hours: int = 0,
    one_off_adjustment: tuple = NO_ADJUSTMENTS,
    ) -> openingTimes:

    start_and_end = string_for_day.split("-")
    if len(start_and_end) == 1:
        # closed
        return CLOSED_ALL_DAY

    start_phrase = start_and_end[0]
    end_phrase = start_and_end[1]

    # Doesn't deal with DST. We will be conservative and only trade 1 hour
    # after and 1 hour before
    adjust_start = 1 + one_off_adjustment[0]
    adjust_end = -1 + one_off_adjustment[-1]

    start_dt = parse_phrase(
        start_phrase, adjustment_hours=adjustment_hours, additional_adjust=adjust_start
    )

    end_dt = parse_phrase(
        end_phrase, adjustment_hours=adjustment_hours, additional_adjust=adjust_end
    )

    return openingTimes(start_dt, end_dt)


def parse_phrase(phrase: str, adjustment_hours: int = 0, additional_adjust: int = 0)\
        -> datetime.datetime:
    total_adjustment = adjustment_hours + additional_adjust
    original_time = datetime.datetime.strptime(phrase, "%Y%m%d:%H%M")
    adjustment = datetime.timedelta(hours=total_adjustment)

    return original_time + adjustment

def get_GMT_offset_hours():
    # this needs to be in private_config.YAML
    # where are the defaults stored that needs to be
    # GMT_offset_hours = 0
    try:
        production_config = get_production_config()
        GMT_offset_hours = production_config.GMT_offset_hours
    except:
        raise Exception("Default is zero, have it in private_config")
    return GMT_offset_hours

def get_time_difference(time_zone_id: str) -> int:
    # Doesn't deal with DST. We will be conservative and only trade 1 hour
    # after and 1 hour before
    # confusingly, IB seem to have changed their time zone codes in 2020
    time_diff_dict = {
        "CST (Central Standard Time)": 6,
        "MET (Middle Europe Time)": -1,
        "EST (Eastern Standard Time)": 5,
        "JST (Japan Standard Time)": -8,
        "US/Eastern": 5,
        "MET": -1,
        "EST": 5,
        "JST": -8,
        "Japan": -8,
        "US/Central": 6,
        "GB-Eire": 0,
        "Hongkong": -7,
        "": 0,
    }
    GMT_offset_hours = get_GMT_offset_hours()
    for k, v in time_diff_dict.items():
        time_diff_dict[k] = v + GMT_offset_hours
    diff_hours = time_diff_dict.get(time_zone_id, None)
    if diff_hours is None:
        raise Exception("Time zone '%s' not found!" % time_zone_id)

    return diff_hours


def one_off_adjustments(symbol: str) -> tuple:
    ## Instrument specific - none needed any more
    ## Leave code unless have problems again

    return NO_ADJUSTMENTS
