import datetime
from ib_insync import ContractDetails as ibContractDetails

from syscore.dateutils import adjust_trading_hours_conservatively

def get_conservative_trading_hours(ib_contract_details: ibContractDetails):
    ## KEEP THE GENERAL IDEA, BUT AT SOME POINT REPLACE WITH A MAPPING FUNCTION
    ##   BASED ON ACTUAL LIQUIDITY
    time_zone_id = ib_contract_details.timeZoneId
    conservative_times = get_conservative_trading_time_UTC(time_zone_id)

    trading_hours = get_trading_hours(ib_contract_details)

    trading_hours_adjusted_to_be_conservative = \
        adjust_trading_hours_conservatively(trading_hours,
            conservative_times = conservative_times)

    return trading_hours_adjusted_to_be_conservative

def get_trading_hours(ib_contract_details: ibContractDetails) -> list:
    try:
        time_zone_id = ib_contract_details.timeZoneId
        time_zone_adjustment = get_time_difference(time_zone_id)
        one_off_adjustment = one_off_adjustments(
            ib_contract_details.contract.symbol)

        trading_hours_string = ib_contract_details.tradingHours
        list_of_open_times = parse_trading_hours_string(
            trading_hours_string,
            adjustment_hours=time_zone_adjustment,
            one_off_adjustment=one_off_adjustment
        )
    except Exception as e:
        raise e

    return list_of_open_times


NO_ADJUSTMENTS = 0,0

def parse_trading_hours_string(
    trading_hours_string: str,
        adjustment_hours: int=0,
        one_off_adjustment: tuple=NO_ADJUSTMENTS
):
    day_by_day = trading_hours_string.split(";")
    list_of_open_times = [
        parse_trading_for_day(
            string_for_day,
            adjustment_hours=adjustment_hours,
            one_off_adjustment=one_off_adjustment
        )
        for string_for_day in day_by_day
    ]

    list_of_open_times = [
        open_time for open_time in list_of_open_times if open_time is not None
    ]

    return list_of_open_times


def parse_trading_for_day(
    string_for_day: str,
        adjustment_hours: int=0,
        one_off_adjustment: tuple=NO_ADJUSTMENTS
):
    start_and_end = string_for_day.split("-")
    if len(start_and_end) == 1:
        # closed
        return None

    start_phrase = start_and_end[0]
    end_phrase = start_and_end[1]

    # Doesn't deal with DST. We will be conservative and only trade 1 hour
    # after and 1 hour before
    adjust_start = 1 + one_off_adjustment[0]
    adjust_end = -1 + one_off_adjustment[-1]

    start_dt = parse_phrase(
        start_phrase,
        adjustment_hours=adjustment_hours,
        additional_adjust=adjust_start)

    end_dt = parse_phrase(
        end_phrase,
        adjustment_hours=adjustment_hours,
        additional_adjust=adjust_end)

    return (start_dt, end_dt)


def parse_phrase(phrase: str, adjustment_hours: int=0, additional_adjust: int=0):
    total_adjustment = adjustment_hours + additional_adjust
    original_time = datetime.datetime.strptime(phrase, "%Y%m%d:%H%M")
    adjustment = datetime.timedelta(hours=total_adjustment)

    return original_time + adjustment


def get_conservative_trading_time_UTC(time_zone_id: str) -> tuple:
    # ALthough many things are liquid all day, we want to be conservative
    # confusingly, IB seem to have changed their time zone codes in 2020
    start_time = 10
    end_time = 16

    time_diff = get_time_difference(time_zone_id)

    adjusted_start_time = datetime.time(hour=start_time + time_diff)
    adjusted_end_time = datetime.time(hour=end_time+time_diff)

    return adjusted_start_time, adjusted_end_time



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
        "": 0
    }
    diff_hours = time_diff_dict.get(time_zone_id, None)
    if diff_hours is None:
        raise Exception("Time zone '%s' not found!" % time_zone_id)

    return diff_hours


def one_off_adjustments(symbol: str) -> tuple:
    adj_dict = dict(EOE=(-9, -5), CAC40=(-9, -5))
    one_off = adj_dict.get(symbol, NO_ADJUSTMENTS)
    return one_off

