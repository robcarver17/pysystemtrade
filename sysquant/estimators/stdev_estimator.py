import datetime
import pandas as pd
import numpy as np

from syscore.pandas.pdutils import (
    apply_with_min_periods,
)
from syscore.pandas.find_data import (
    get_row_of_df_aligned_to_weights_as_dict,
    get_max_index_before_datetime,
)
from syscore.pandas.frequency import how_many_times_a_year_is_pd_frequency
from syscore.dateutils import BUSINESS_DAYS_IN_YEAR

from sysquant.fitting_dates import fitDates
from sysquant.estimators.generic_estimator import (
    genericEstimator,
    exponentialEstimator,
    Estimate,
)


class stdevEstimates(dict, Estimate):
    def assets_with_data(self) -> list:
        return [asset_name for asset_name in self.keys() if ~np.isnan(self[asset_name])]

    def subset(self, subset_of_asset_names: list):
        return stdevEstimates(
            [(asset_name, self[asset_name]) for asset_name in subset_of_asset_names]
        )

    def assets_with_missing_data(self) -> list:
        return [asset_name for asset_name in self.keys() if np.isnan(self[asset_name])]

    def list_in_key_order(self, list_of_keys: list) -> list:
        return [self[asset_name] for asset_name in list_of_keys]

    def list_of_keys(self) -> list:
        return list(self.keys())


class seriesOfStdevEstimates(pd.DataFrame):
    def get_stdev_on_date(self, relevant_date: datetime.datetime) -> stdevEstimates:
        if relevant_date < self.index[0]:
            stdev_as_dict = get_row_of_df_aligned_to_weights_as_dict(
                df=self, relevant_date=self.index[0]
            )

        else:
            stdev_as_dict = get_row_of_df_aligned_to_weights_as_dict(
                df=self, relevant_date=relevant_date
            )
        return stdevEstimates(stdev_as_dict)

    def shocked(self, shock_quantile=0.99, roll_years=10, bfill=True):
        min_periods = int(np.ceil(2 / shock_quantile))
        roll_bus_days = int(roll_years * BUSINESS_DAYS_IN_YEAR)
        align_daily = self.resample("1B").ffill()
        shocked = align_daily.rolling(roll_bus_days, min_periods=min_periods).quantile(
            shock_quantile
        )
        if bfill:
            shocked = shocked.bfill()
        align_shocked = shocked.reindex(self.index).ffill()

        return seriesOfStdevEstimates(align_shocked)


class exponentialStdev(exponentialEstimator):
    def __init__(
        self,
        data_for_stdev: pd.DataFrame,
        ew_lookback: int = 250,
        min_periods: int = 20,
        length_adjustment: int = 1,
        frequency: str = "W",
        **_ignored_kwargs,
    ):

        super().__init__(
            data_for_stdev,
            ew_lookback=ew_lookback,
            min_periods=min_periods,
            length_adjustment=length_adjustment,
            frequency=frequency,
            **_ignored_kwargs,
        )

    @property
    def frequency(self) -> str:
        return self.other_kwargs["frequency"]

    def perform_calculations(
        self,
        data_for_stdev: pd.DataFrame,
        adjusted_lookback=500,
        adjusted_min_periods=20,
        **other_kwargs,
    ) -> pd.DataFrame:

        stdev_calculations = exponential_std_deviation(
            data_for_stdev,
            ew_lookback=adjusted_lookback,
            min_periods=adjusted_min_periods,
        )

        return stdev_calculations

    def get_estimate_for_fitperiod_with_data(
        self, fit_period: fitDates
    ) -> stdevEstimates:
        exponential_std_deviation = self.calculations

        last_index = get_max_index_before_datetime(
            exponential_std_deviation.index, fit_period.fit_end
        )
        if last_index is None:
            return empty_stdev(self.data)

        stdev = stdevEstimates(exponential_std_deviation.iloc[last_index])
        stdev = annualise_stdev_estimate(stdev, frequency=self.frequency)

        return stdev


def exponential_std_deviation(
    data_for_stdev: pd.DataFrame,
    ew_lookback: int = 250,
    min_periods: int = 20,
    **_ignored_kwargs,
) -> pd.DataFrame:

    exponential_stdev = data_for_stdev.ewm(
        span=ew_lookback, min_periods=min_periods
    ).std()

    return exponential_stdev


class stdevEstimator(genericEstimator):
    def __init__(
        self, data_for_stdev: pd.DataFrame, using_exponent: bool = True, **kwargs
    ):
        super().__init__(data_for_stdev, using_exponent=using_exponent, **kwargs)

    def estimate_if_no_data(self) -> stdevEstimates:
        return empty_stdev(self.data)

    def calculate_estimate_normally(self, fit_period: fitDates) -> stdevEstimates:
        data_for_stdev = self.data
        kwargs_for_estimator = self.kwargs_for_estimator
        stdev = stdev_estimator_for_subperiod(
            data_for_stdev, fit_period=fit_period, **kwargs_for_estimator
        )

        return stdev

    def get_exponential_estimator_for_entire_dataset(self) -> exponentialStdev:
        kwargs_for_estimator = self.kwargs_for_estimator
        exponential_estimator = exponentialStdev(self.data, **kwargs_for_estimator)

        return exponential_estimator


def stdev_estimator_for_subperiod(
    data_for_stdev: pd.DataFrame,
    fit_period: fitDates,
    min_periods: int = 20,
    frequency: str = "W",
    **_ignored_kwargs,
) -> stdevEstimates:
    subperiod_data = data_for_stdev[fit_period.fit_start : fit_period.fit_end]

    stdev_values = simple_vol_estimator_with_min_periods(
        subperiod_data, min_periods=min_periods
    )
    asset_names = data_for_stdev.columns
    stdev = stdevEstimates(
        [(asset_name, stdev) for asset_name, stdev in zip(asset_names, stdev_values)]
    )

    stdev = annualise_stdev_estimate(stdev, frequency=frequency)

    return stdev


def simple_vol_estimator_with_min_periods(x, min_periods=20) -> list:
    vol = x.apply(
        apply_with_min_periods,
        axis=0,
        min_periods=min_periods,
        my_func=np.nanstd,
    )

    stdev_list = list(vol)

    return stdev_list


def empty_stdev(data_for_stdev: pd.DataFrame) -> stdevEstimates:
    columns = data_for_stdev.columns

    return stdevEstimates([(asset_name, np.nan) for asset_name in columns])


def annualise_stdev_estimate(stdev: stdevEstimates, frequency: str) -> stdevEstimates:
    return stdevEstimates(
        [
            (asset_name, annualised_stdev(stdev_value, frequency=frequency))
            for asset_name, stdev_value in stdev.items()
        ]
    )


def annualised_stdev(stdev_value: float, frequency: str):
    how_many_times_a_year = how_many_times_a_year_is_pd_frequency(frequency)

    return stdev_value * (how_many_times_a_year**0.5)
