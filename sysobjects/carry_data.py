import numpy as np
import pandas as pd
from syscore.dateutils import CALENDAR_DAYS_IN_YEAR
from syscore.pandas.pdutils import uniquets
from syscore.pandas.strategy_functions import apply_abs_min


class rawCarryData(pd.DataFrame):
    def roll_differentials(
        self, floor_date_diff: float = 1 / CALENDAR_DAYS_IN_YEAR
    ) -> pd.Series:
        raw_differential = self.raw_differential()

        ## This prevents the roll differential from being zero in a corner
        ##     case when the two contract months match - it has to be at least one day

        floored_differential = apply_abs_min(raw_differential, floor_date_diff)
        unique_differential = uniquets(floored_differential)

        return unique_differential

    def raw_differential(self) -> pd.Series:
        price_contract_as_frac = self.price_contract_as_year_frac()
        carry_contract_as_frac = self.carry_contract_as_year_frac()

        return carry_contract_as_frac - price_contract_as_frac

    def price_contract_as_year_frac(self) -> pd.Series:
        return _total_year_frac_from_contract_series(self.price_contract_as_float())

    def carry_contract_as_year_frac(self) -> pd.Series:
        return _total_year_frac_from_contract_series(self.carry_contract_as_float())

    def raw_futures_roll(self) -> pd.Series:
        raw_roll = self.price - self.carry

        raw_roll[raw_roll == 0] = np.nan

        raw_roll = uniquets(raw_roll)

        return raw_roll

    def carry_contract_as_float(self) -> pd.Series:
        carry_contract_as_float = self.carry_contract.astype(float)
        return carry_contract_as_float

    def price_contract_as_float(self) -> pd.Series:
        price_contract_as_float = self.price_contract.astype(float)
        return price_contract_as_float

    @property
    def carry_contract(self) -> pd.Series:
        return self.CARRY_CONTRACT

    @property
    def price_contract(self) -> pd.Series:
        return self.PRICE_CONTRACT

    @property
    def price(self) -> pd.Series:
        return self.PRICE

    @property
    def carry(self) -> pd.Series:
        return self.CARRY


def _total_year_frac_from_contract_series(x):
    years = _year_from_contract_series(x)
    month_frac = _month_as_year_frac_from_contract_series(x)

    return years + month_frac


def _year_from_contract_series(x):
    return x.floordiv(10000)


def _month_as_year_frac_from_contract_series(x):
    return _month_from_contract_series(x) / 12.0


def _month_from_contract_series(x):
    return x.mod(10000) / 100.0
