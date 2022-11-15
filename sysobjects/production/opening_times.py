import datetime
from dataclasses import dataclass

from syscore.dateutils import SECONDS_PER_HOUR


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