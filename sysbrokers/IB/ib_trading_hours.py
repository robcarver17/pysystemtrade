import datetime
from ib_insync import ContractDetails as ibContractDetails

from sysdata.config.private_directory import get_full_path_for_private_config
from sysobjects.production.trading_hours.trading_hours import (
    tradingHours,
    listOfTradingHours,
)
from syscore.fileutils import does_filename_exist
from sysdata.config.production_config import get_production_config
from sysdata.production.trading_hours import read_trading_hours

IB_CONFIG_TRADING_HOURS_FILE = "sysbrokers.IB.ib_config_trading_hours.yaml"
PRIVATE_CONFIG_TRADING_HOURS_FILE = get_full_path_for_private_config(
    "private_config_trading_hours.yaml"
)


def get_saved_trading_hours():
    if does_filename_exist(PRIVATE_CONFIG_TRADING_HOURS_FILE):
        return read_trading_hours(PRIVATE_CONFIG_TRADING_HOURS_FILE)
    else:
        return read_trading_hours(IB_CONFIG_TRADING_HOURS_FILE)


def get_trading_hours_from_contract_details(
    ib_contract_details: ibContractDetails,
) -> listOfTradingHours:
    try:
        time_zone_id = ib_contract_details.timeZoneId
        time_zone_adjustment = get_time_difference(time_zone_id)

        trading_hours_string = ib_contract_details.tradingHours
        list_of_open_times = parse_trading_hours_string(
            trading_hours_string, adjustment_hours=time_zone_adjustment
        )
    except Exception as e:
        raise e

    return list_of_open_times


NO_ADJUSTMENTS = 0, 0
CLOSED_ALL_DAY = object()


def parse_trading_hours_string(
    trading_hours_string: str,
    adjustment_hours: int = 0,
) -> listOfTradingHours:

    day_by_day = trading_hours_string.split(";")
    list_of_open_times = [
        parse_trading_for_day(string_for_day, adjustment_hours=adjustment_hours)
        for string_for_day in day_by_day
    ]

    list_of_open_times = [
        open_time for open_time in list_of_open_times if open_time is not CLOSED_ALL_DAY
    ]

    list_of_open_times = listOfTradingHours(list_of_open_times)

    return list_of_open_times


def parse_trading_for_day(
    string_for_day: str, adjustment_hours: int = 0
) -> tradingHours:

    start_and_end = string_for_day.split("-")
    if len(start_and_end) == 1:
        # closed
        return CLOSED_ALL_DAY

    start_phrase = start_and_end[0]
    end_phrase = start_and_end[1]

    # Doesn't deal with DST. We will be conservative and only trade 1 hour
    # after and 1 hour before
    adjust_start = 1
    adjust_end = -1

    start_dt = parse_phrase(
        start_phrase, adjustment_hours=adjustment_hours, additional_adjust=adjust_start
    )

    end_dt = parse_phrase(
        end_phrase, adjustment_hours=adjustment_hours, additional_adjust=adjust_end
    )

    return tradingHours(start_dt, end_dt)


def parse_phrase(
    phrase: str, adjustment_hours: int = 0, additional_adjust: int = 0
) -> datetime.datetime:
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
    # some of these are legacy codes which could be removed
    time_diff_dict = {
        "CST (Central Standard Time)": 6,
        "MET (Middle Europe Time)": -1,
        "EST (Eastern Standard Time)": 5,
        "JST (Japan Standard Time)": -9,
        "US/Eastern": 5,
        "MET": -1,
        "EST": 5,
        "JST": -9,
        "Japan": -9,
        "US/Central": 6,
        "GB-Eire": 0,
        "Hongkong": -8,
        "Australia/NSW": -11,
        "": 0,
    }
    GMT_offset_hours = get_GMT_offset_hours()
    for k, v in time_diff_dict.items():
        time_diff_dict[k] = v + GMT_offset_hours
    diff_hours = time_diff_dict.get(time_zone_id, None)
    if diff_hours is None:
        raise Exception("Time zone '%s' not found!" % time_zone_id)

    return diff_hours
