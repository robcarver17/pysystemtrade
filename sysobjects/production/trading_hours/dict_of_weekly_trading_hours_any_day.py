from typing import Dict

from sysobjects.production.trading_hours.weekly_trading_hours_any_day import (
    weekdayDictOfListOfTradingHoursAnyDay,
)


class dictOfDictOfWeekdayTradingHours(dict):
    ## keys are instruments, values are lists of opening times
    def __init__(
        self, dict_of_dict_of_times: Dict[str, weekdayDictOfListOfTradingHoursAnyDay]
    ):
        super().__init__(dict_of_dict_of_times)

    def to_simple_dict(self) -> dict:
        ## allows yaml write
        simple_dict_of_weekday_opening_times = dict(
            [
                (instrument_code, self[instrument_code].to_simple_dict())
                for instrument_code in list(self.keys())
            ]
        )

        return simple_dict_of_weekday_opening_times

    @classmethod
    def from_simple_dict(cls, simple_dict: dict):
        dict_of_weekday_opening_times = dict(
            [
                (
                    instrument_code,
                    weekdayDictOfListOfTradingHoursAnyDay.from_simple_dict(
                        simple_dict[instrument_code]
                    ),
                )
                for instrument_code in list(simple_dict.keys())
            ]
        )

        return cls(dict_of_weekday_opening_times)
