import datetime

from syscore.dateutils import SECONDS_PER_HOUR


class tradingStartAndEnd(object):
    def __init__(self, hour_tuple):
        self._start_time = hour_tuple[0]
        self._end_time = hour_tuple[1]

    def okay_to_trade_now(self):
        datetime_now = datetime.datetime.now()
        if datetime_now >= self._start_time and datetime_now <= self._end_time:
            return True
        else:
            return False

    def less_than_one_hour_left(self):
        datetime_now = datetime.datetime.now()
        time_left = self._end_time - datetime_now
        if time_left.total_seconds() < SECONDS_PER_HOUR:
            return True
        else:
            return False


class manyTradingStartAndEnd(object):
    def __init__(self, list_of_trading_hours):
        """

        :param list_of_trading_hours: list of tuples, both datetime, first is start and second is end
        """

        my_start_and_end = []
        for hour_tuple in list_of_trading_hours:
            this_period = tradingStartAndEnd(hour_tuple)
            my_start_and_end.append(this_period)

        self._my_start_and_end = my_start_and_end

    def okay_to_trade_now(self):
        for check_period in self._my_start_and_end:
            if check_period.okay_to_trade_now():
                return True
        return False

    def less_than_one_hour_left(self):
        for check_period in self._my_start_and_end:
            if check_period.okay_to_trade_now():
                if check_period.less_than_one_hour_left():
                    return True
                else:
                    return False

        return None
