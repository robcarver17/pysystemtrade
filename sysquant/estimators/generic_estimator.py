import pandas as pd
import numpy as np
from sysquant.fitting_dates import fitDates


class Estimate:
    def subset(self, subset_of_asset_names: list):
        raise NotImplementedError

    def assets_with_missing_data(self) -> list:
        raise NotImplementedError

    def list_in_key_order(self, list_of_keys: list) -> list:
        raise NotImplementedError

    def list_of_keys(self):
        raise NotImplementedError

    def as_np(self) -> np.array:
        as_list = self.as_list()
        return np.array(as_list)

    def as_list(self) -> list:
        keys = list(self.list_of_keys())
        as_list = self.list_in_key_order(keys)

        return as_list


class exponentialEstimator(object):
    def __init__(
        self,
        data,
        ew_lookback: int = 250,
        min_periods: int = 20,
        length_adjustment: int = 1,
        **other_kwargs,
    ):
        adjusted_lookback = ew_lookback * length_adjustment
        adjusted_min_periods = min_periods * length_adjustment

        calculations = self.perform_calculations(
            data,
            adjusted_lookback=adjusted_lookback,
            adjusted_min_periods=adjusted_min_periods,
            **other_kwargs,
        )

        self._calculations = calculations
        self._data = data
        self._other_kwargs = other_kwargs

    def perform_calculations(
        self,
        data: pd.DataFrame,
        adjusted_lookback=500,
        adjusted_min_periods=20,
        **other_kwargs,
    ):
        """
        eg    return self.data.ewm(span=adjusted_lookback,
                          min_periods=adjusted_min_periods).mean()

        """
        raise NotImplementedError("Need to inherit dont' use")

    @property
    def calculations(self):
        return self._calculations

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def other_kwargs(self) -> dict:
        return self._other_kwargs

    def missing_data(self) -> Estimate:
        raise NotImplementedError("Have to inherit from base class")

    def get_estimate_for_fitperiod(self, fit_period: fitDates) -> Estimate:
        if fit_period.no_data:
            return self.missing_data()

        estimate = self.get_estimate_for_fitperiod_with_data(fit_period)

        return estimate

    def get_estimate_for_fitperiod_with_data(self, fit_period: fitDates) -> Estimate:
        raise NotImplementedError("Have to inherit from base class")


class genericEstimator(object):
    def __init__(self, data: pd.DataFrame, using_exponent: bool = True, **kwargs):
        self._data = data
        self._using_exponent = using_exponent
        self._kwargs = kwargs

    @property
    def using_exponent(self) -> bool:
        return self._using_exponent

    @property
    def data(self):
        return self._data

    @property
    def kwargs_for_estimator(self) -> dict:
        return self._kwargs

    def calculate_estimate_for_period(self, fit_period: fitDates):
        if fit_period.no_data:
            return self.estimate_if_no_data()

        if self.using_exponent:
            estimate = self.calculate_estimate_using_exponential_data_for_period(
                fit_period
            )
        else:
            estimate = self.calculate_estimate_normally(fit_period)

        return estimate

    def calculate_estimate_normally(self, fit_period: fitDates):
        raise NotImplementedError("Have to inherit from base class")

    def calculate_estimate_using_exponential_data_for_period(
        self, fit_period: fitDates
    ):
        exponential_estimator = self.get_exponential_estimator_for_entire_dataset()

        estimate = exponential_estimator.get_estimate_for_fitperiod(fit_period)

        return estimate

    def get_exponential_estimator_for_entire_dataset(self) -> exponentialEstimator:
        exponential_estimator = getattr(self, "_stored_exponential_estimator", None)
        if exponential_estimator is None:
            exponential_estimator = (
                self.calculate_exponential_estimator_for_entire_dataset()
            )
            self._stored_exponential_estimator = exponential_estimator

        return exponential_estimator

    def calculate_exponential_estimator_for_entire_dataset(
        self,
    ) -> exponentialEstimator:
        kwargs_for_estimator = self.kwargs_for_estimator
        exponential_estimator = exponentialEstimator(self.data, **kwargs_for_estimator)

        return exponential_estimator

    def estimate_if_no_data(self):
        raise NotImplementedError("Need to inherit from base class")
