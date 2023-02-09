import pandas as pd
import datetime

from syscore.exceptions import missingData

TOTAL_MARGIN = "_TOTAL_MARGIN"


class seriesOfMargin(pd.Series):
    def final_value(self) -> float:
        if len(self) == 0:
            raise missingData
        return self.values[-1]

    def add_value(self, value: float, dateref=datetime.datetime.now()):

        return seriesOfMargin(self.append(pd.Series([value], index=[dateref])))


class marginData(object):
    def get_series_of_total_margin(self) -> seriesOfMargin:
        total_margin = self.get_series_of_strategy_margin(TOTAL_MARGIN)
        return total_margin

    def get_current_total_margin(self) -> float:
        current_margin = self.get_current_strategy_margin(TOTAL_MARGIN)
        return current_margin

    def add_total_margin_entry(self, margin_entry: float):
        self.add_strategy_margin_entry(
            margin_entry=margin_entry, strategy_name=TOTAL_MARGIN
        )

    def get_list_of_strategies_with_margin(self) -> list:
        list_of_strategies = self._get_list_of_strategies_with_margin_including_total()
        try:
            list_of_strategies.remove(TOTAL_MARGIN)
        except:
            # missing no sweat
            pass

        return list_of_strategies

    def get_current_strategy_margin(self, strategy_name: str) -> float:
        series_of_margin = self.get_series_of_strategy_margin(
            strategy_name=strategy_name
        )

        return series_of_margin.final_value()

    def add_strategy_margin_entry(self, margin_entry: float, strategy_name: str):
        existing_series = self.get_series_of_strategy_margin(strategy_name)
        new_series = existing_series.add_value(margin_entry)
        self._write_series_of_strategy_margin(
            strategy_name, series_of_margin=new_series
        )

    def get_series_of_strategy_margin(self, strategy_name: str) -> seriesOfMargin:
        raise NotImplementedError

    def _get_list_of_strategies_with_margin_including_total(self) -> list:
        raise NotImplementedError

    def _write_series_of_strategy_margin(
        self, strategy_name: str, series_of_margin: seriesOfMargin
    ):
        raise NotImplementedError
