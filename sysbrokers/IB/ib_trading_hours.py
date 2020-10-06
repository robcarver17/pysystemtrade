import datetime


def get_trading_hours(ib_contract_details):
    try:
        time_zone_id = ib_contract_details.timeZoneId
        time_zone_adjustment = get_time_difference(time_zone_id)
        one_off_adjustment = one_off_adjustments(
            ib_contract_details.contract.symbol)
        trading_hours_string = ib_contract_details.tradingHours
        list_of_open_times = parse_trading_hours_string(
            trading_hours_string,
            adjustment_hours=time_zone_adjustment,
            one_off_adjustment=one_off_adjustment,
        )
    except Exception as e:
        raise e

    return list_of_open_times


def parse_trading_hours_string(
    trading_hours_string, adjustment_hours=0, one_off_adjustment=[0, 0]
):
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
        open_time for open_time in list_of_open_times if open_time is not None
    ]

    return list_of_open_times


def parse_trading_for_day(
    string_for_day, adjustment_hours=0, one_off_adjustment=[0, 0]
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


def parse_phrase(phrase, adjustment_hours=0, additional_adjust=0):
    total_adjustment = adjustment_hours + additional_adjust
    original_time = datetime.datetime.strptime(phrase, "%Y%m%d:%H%M")
    adjustment = datetime.timedelta(hours=total_adjustment)

    return original_time + adjustment


def get_time_difference(time_zone_id):
    # Doesn't deal with DST. We will be conservative and only trade 1 hour
    # after and 1 hour before
    time_diff_dict = {
        "CST (Central Standard Time)": 6,
        "MET (Middle Europe Time)": -1,
        "EST (Eastern Standard Time)": 5,
        "JST (Japan Standard Time)": -8,
    }
    diff_hours = time_diff_dict.get(time_zone_id, None)
    if diff_hours is None:
        raise Exception("Time zone '%s' not found!" % time_zone_id)

    return diff_hours


def one_off_adjustments(symbol):
    adj_dict = dict(EOE=[-9, -5], CAC40=[-9, -5])
    one_off = adj_dict.get(symbol, [0, 0])
    return one_off
