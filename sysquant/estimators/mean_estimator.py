import pandas as pd
import numpy as np

from syscore.pandas.pdutils import (
    apply_with_min_periods,
)
from syscore.pandas.find_data import get_max_index_before_datetime
from syscore.pandas.frequency import how_many_times_a_year_is_pd_frequency

from sysquant.fitting_dates import fitDates
from sysquant.estimators.generic_estimator import (
    genericEstimator,
    exponentialEstimator,
    Estimate,
)


class meanEstimates(dict, Estimate):
    def subset(self, subset_of_asset_names: list):
        return meanEstimates(
            [(asset_name, self[asset_name]) for asset_name in subset_of_asset_names]
        )

    def assets_with_missing_data(self) -> list:
        return [asset_name for asset_name in self.keys() if np.isnan(self[asset_name])]

    def list_in_key_order(self, list_of_keys: list) -> list:
        return [self[asset_name] for asset_name in list_of_keys]

    def list_of_keys(self) -> list:
        return list(self.keys())


class exponentialMeans(exponentialEstimator):
    def __init__(
        self,
        data_for_mean: pd.DataFrame,
        ew_lookback: int = 250,
        min_periods: int = 20,
        length_adjustment: int = 1,
        frequency: str = "W",
        **_ignored_kwargs,
    ):

        super().__init__(
            data_for_mean,
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
        data: pd.DataFrame,
        adjusted_lookback=500,
        adjusted_min_periods=20,
        **_other_kwargs,
    ) -> pd.DataFrame:

        mean_calculations = exponential_mean(
            data, ew_lookback=adjusted_lookback, min_periods=adjusted_min_periods
        )

        return mean_calculations

    def get_estimate_for_fitperiod_with_data(
        self, fit_period: fitDates
    ) -> meanEstimates:
        exponential_mean_df = self.calculations

        last_index = get_max_index_before_datetime(
            exponential_mean_df.index, fit_period.fit_end
        )
        if last_index is None:
            return empty_stdev(self.data)

        mean = meanEstimates(exponential_mean_df.iloc[last_index])
        mean = annualise_mean_estimate(mean, frequency=self.frequency)

        return mean


def exponential_mean(
    data_for_mean: pd.DataFrame, ew_lookback: int = 250, min_periods: int = 20
) -> pd.DataFrame:

    exponential_mean = data_for_mean.ewm(
        span=ew_lookback, min_periods=min_periods
    ).mean()

    return exponential_mean


class meanEstimator(genericEstimator):
    def __init__(
        self,
        data_for_mean: pd.DataFrame,
        using_exponent: bool = True,
        frequency: str = "W",
        **kwargs,
    ):

        super().__init__(data_for_mean, using_exponent=using_exponent, **kwargs)

    def calculate_estimate_normally(self, fit_period: fitDates) -> meanEstimates:
        data_for_mean = self.data
        kwargs_for_estimator = self.kwargs_for_estimator
        mean = mean_estimator_for_subperiod(
            data_for_mean, fit_period=fit_period, **kwargs_for_estimator
        )

        return mean

    def get_exponential_estimator_for_entire_dataset(self) -> exponentialMeans:
        kwargs_for_estimator = self.kwargs_for_estimator
        exponential_estimator = exponentialMeans(self.data, **kwargs_for_estimator)

        return exponential_estimator

    def estimate_if_no_data(self) -> meanEstimates:
        return empty_mean(self.data)


def mean_estimator_for_subperiod(
    data_for_mean: pd.DataFrame,
    fit_period: fitDates,
    min_periods: int = 20,
    frequency: str = "W",
    **_ignored_kwargs,
) -> meanEstimates:
    subperiod_data = data_for_mean[fit_period.fit_start : fit_period.fit_end]

    mean_values = simple_mean_estimator_with_min_periods(
        subperiod_data, min_periods=min_periods
    )
    asset_names = data_for_mean.columns
    mean = meanEstimates(
        [
            (asset_name, mean_value)
            for asset_name, mean_value in zip(asset_names, mean_values)
        ]
    )

    mean = annualise_mean_estimate(mean, frequency=frequency)

    return mean


def simple_mean_estimator_with_min_periods(x, min_periods=20) -> list:
    mean = x.apply(
        apply_with_min_periods,
        axis=0,
        min_periods=min_periods,
        my_func=np.nanmean,
    )

    mean_list = list(mean)

    return mean_list


def empty_mean(data_for_mean: pd.DataFrame) -> meanEstimates:
    columns = data_for_mean.columns

    return meanEstimates([(asset_name, np.nan) for asset_name in columns])


def annualise_mean_estimate(mean: meanEstimates, frequency: str) -> meanEstimates:

    return meanEstimates(
        [
            (asset_name, annualised_mean(mean_value, frequency=frequency))
            for asset_name, mean_value in mean.items()
        ]
    )


def annualised_mean(mean: float, frequency: str):
    how_many_times_a_year = how_many_times_a_year_is_pd_frequency(frequency)

    return mean * how_many_times_a_year
