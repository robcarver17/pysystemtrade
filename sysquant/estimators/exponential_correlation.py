import datetime
import pandas as pd
from syscore.genutils import str2Bool
from syscore.objects import missing_data, arg_not_supplied
from sysquant.fitting_dates import fitDates
from sysquant.estimators.correlations import correlationEstimate, create_boring_corr_matrix
from sysquant.estimators.generic_estimator import exponentialEstimator

class exponentialCorrelation(exponentialEstimator):
    def __init__(self, data_for_correlation,
                 ew_lookback:int =250,
                 min_periods:int=20,
                 cleaning:bool = True,
                 floor_at_zero:bool = True,
                 length_adjustment: int = 1,
                 **_ignored_kwargs):

        super().__init__(data_for_correlation,
                         ew_lookback=ew_lookback,
                         min_periods=min_periods,
                         cleaning = cleaning,
                         floor_at_zero=floor_at_zero,
                         length_adjustment=length_adjustment,
                         **_ignored_kwargs)



    def perform_calculations(self, data_for_correlation: pd.DataFrame,
                             adjusted_lookback = 500,
                                  adjusted_min_periods = 20,
                             **other_kwargs):

        correlation_calculations = exponentialCorrelationResults(data_for_correlation,
                                                                 ew_lookback=adjusted_lookback,
                                                                 min_periods=adjusted_min_periods)

        return correlation_calculations

    @property
    def cleaning(self) -> bool:
        cleaning = str2Bool(self.other_kwargs['cleaning'])

        return cleaning

    @property
    def floor_at_zero(self) -> bool:
        floor_at_zero = str2Bool(self.other_kwargs['floor_at_zero'])
        return floor_at_zero

    @property
    def clip(self) -> float:
        clip = self.other_kwargs.get('clip',arg_not_supplied)
        return  clip

    def missing_data(self):
        asset_names = list(self.data.columns)
        return create_boring_corr_matrix(len(asset_names),
                                         columns = asset_names)

    def get_estimate_for_fitperiod_with_data(self, fit_period: fitDates) -> correlationEstimate:

        raw_corr_matrix = self._get_raw_corr_for_datetime(fit_period)

        cleaning = self.cleaning
        if cleaning:
            data_for_correlation = self.data
            offdiag = self.other_kwargs.get('offdiag', 0.99)
            corr_matrix = raw_corr_matrix.clean_corr_matrix_given_data(
                                                               fit_period,
                                                               data_for_correlation,
                                                                offdiag=offdiag)
        else:
            corr_matrix = raw_corr_matrix

        floor_at_zero = self.floor_at_zero
        if floor_at_zero:
            corr_matrix = corr_matrix.floor_correlation_matrix(floor = 0.0)

        clip = self.clip
        corr_matrix = corr_matrix.clip_correlation_matrix(clip=clip)

        return corr_matrix

    def _get_raw_corr_for_datetime(self, fit_period: fitDates) -> correlationEstimate:
        correlation_calculations = self.calculations
        last_date_in_fit_period = fit_period.fit_end
        ## some kind of access
        raw_corr_matrix = correlation_calculations.\
            last_valid_cor_matrix_for_date(last_date_in_fit_period)

        return raw_corr_matrix



class exponentialCorrelationResults(object):
    def __init__(self, data_for_correlation,
                 ew_lookback:int =250,
                 min_periods:int=20,
                 **_ignored_kwargs):

        columns = data_for_correlation.columns
        self._columns = columns

        raw_correlations = data_for_correlation.ewm(
            span=ew_lookback,
            min_periods=min_periods, ignore_na=True).corr(
            pairwise=True, ignore_na=True)

        self._raw_correlations = raw_correlations

    @property
    def raw_correlations(self):
        return self._raw_correlations

    def last_valid_cor_matrix_for_date(self, date_point: datetime.datetime) -> correlationEstimate:
        raw_correlations = self.raw_correlations
        corr_matrix_values = \
                raw_correlations[raw_correlations.index.get_level_values(0) < date_point].\
                tail(self.size_of_matrix).values

        return correlationEstimate(values=corr_matrix_values, columns=self.columns)

    @property
    def size_of_matrix(self) -> int:
        return len(self.columns)

    @property
    def columns(self) -> list:
        return self._columns
