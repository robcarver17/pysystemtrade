import datetime
import pandas as pd
from syscore.genutils import str2Bool
from syscore.constants import arg_not_supplied
from sysquant.fitting_dates import fitDates
from sysquant.estimators.correlations import (
    correlationEstimate,
    create_boring_corr_matrix,
    modify_correlation,
)
from sysquant.estimators.generic_estimator import exponentialEstimator


class exponentialCorrelation(exponentialEstimator):
    def __init__(
        self,
        data_for_correlation,
        ew_lookback: int = 250,
        min_periods: int = 20,
        cleaning: bool = True,
        floor_at_zero: bool = True,
        length_adjustment: int = 1,
        shrinkage_parameter: float = 0.0,
        offdiag: float = 0.99,
        **_ignored_kwargs,
    ):

        super().__init__(
            data_for_correlation,
            ew_lookback=ew_lookback,
            min_periods=min_periods,
            cleaning=cleaning,
            floor_at_zero=floor_at_zero,
            length_adjustment=length_adjustment,
            shrinkage_parameter=shrinkage_parameter,
            offdiag=offdiag,
            **_ignored_kwargs,
        )

    def perform_calculations(
        self,
        data_for_correlation: pd.DataFrame,
        adjusted_lookback=500,
        adjusted_min_periods=20,
        **other_kwargs,
    ):

        correlation_calculations = exponentialCorrelationResults(
            data_for_correlation,
            ew_lookback=adjusted_lookback,
            min_periods=adjusted_min_periods,
        )

        return correlation_calculations

    @property
    def offdiag(self) -> float:
        return self.other_kwargs["offdiag"]

    @property
    def cleaning(self) -> bool:
        cleaning = str2Bool(self.other_kwargs["cleaning"])

        return cleaning

    @property
    def shrinkage_parameter(self) -> float:
        shrinkage_parameter = float(self.other_kwargs["shrinkage_parameter"])
        return shrinkage_parameter

    @property
    def floor_at_zero(self) -> bool:
        floor_at_zero = str2Bool(self.other_kwargs["floor_at_zero"])
        return floor_at_zero

    @property
    def clip(self) -> float:
        clip = self.other_kwargs.get("clip", arg_not_supplied)
        return clip

    def missing_data(self):
        asset_names = list(self.data.columns)
        return create_boring_corr_matrix(len(asset_names), columns=asset_names)

    def get_estimate_for_fitperiod_with_data(
        self, fit_period: fitDates = arg_not_supplied
    ) -> correlationEstimate:

        if fit_period is arg_not_supplied:
            fit_period = self._get_default_fit_period_cover_all_data()

        raw_corr_matrix = self._get_raw_corr_for_fitperiod(fit_period)

        cleaning = self.cleaning
        if cleaning:
            data_for_correlation = self.data
            offdiag = self.offdiag
            corr_matrix = raw_corr_matrix.clean_corr_matrix_given_data(
                fit_period, data_for_correlation, offdiag=offdiag
            )
        else:
            corr_matrix = raw_corr_matrix

        floor_at_zero = self.floor_at_zero
        clip = self.clip
        shrinkage = self.shrinkage_parameter

        corr_matrix = modify_correlation(
            corr_matrix, floor_at_zero=floor_at_zero, shrinkage=shrinkage, clip=clip
        )

        return corr_matrix

    def _get_default_fit_period_cover_all_data(self) -> fitDates:
        last_date_in_fit_period = self.data.last_valid_index()
        first_date_in_fit_period = self.data.first_valid_index()

        fit_period = fitDates(
            period_start=first_date_in_fit_period,
            period_end=last_date_in_fit_period,
            fit_start=first_date_in_fit_period,
            fit_end=last_date_in_fit_period,
        )

        return fit_period

    def _get_raw_corr_for_fitperiod(self, fit_period: fitDates) -> correlationEstimate:
        last_date_in_fit_period = fit_period.fit_end

        return self._get_raw_corr_period_ends_at_date(last_date_in_fit_period)

    def _get_raw_corr_period_ends_at_date(
        self, last_date_in_fit_period: datetime.datetime
    ) -> correlationEstimate:
        correlation_calculations = self.calculations
        raw_corr_matrix = correlation_calculations.last_valid_cor_matrix_for_date(
            last_date_in_fit_period
        )

        return raw_corr_matrix


class exponentialCorrelationResults(object):
    def __init__(
        self,
        data_for_correlation,
        ew_lookback: int = 250,
        min_periods: int = 20,
        **_ignored_kwargs,
    ):

        columns = data_for_correlation.columns
        self._columns = columns

        raw_correlations = data_for_correlation.ewm(
            span=ew_lookback, min_periods=min_periods, ignore_na=True
        ).corr(pairwise=True, ignore_na=True)

        self._raw_correlations = raw_correlations

    @property
    def raw_correlations(self):
        return self._raw_correlations

    def last_valid_cor_matrix_for_date(
        self, date_point: datetime.datetime
    ) -> correlationEstimate:
        raw_correlations = self.raw_correlations
        columns = self.columns

        return last_valid_cor_matrix_for_date(
            raw_correlations=raw_correlations, date_point=date_point, columns=columns
        )

    @property
    def size_of_matrix(self) -> int:
        return len(self.columns)

    @property
    def columns(self) -> list:
        return self._columns


def last_valid_cor_matrix_for_date(
    raw_correlations: pd.DataFrame, columns: list, date_point: datetime.datetime
) -> correlationEstimate:

    size_of_matrix = len(columns)
    corr_matrix_values = (
        raw_correlations[raw_correlations.index.get_level_values(0) < date_point]
        .tail(size_of_matrix)
        .values
    )

    return correlationEstimate(values=corr_matrix_values, columns=columns)
