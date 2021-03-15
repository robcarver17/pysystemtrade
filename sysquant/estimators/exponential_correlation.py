import datetime
from syscore.genutils import str2Bool
from syscore.objects import missing_data
from sysquant.fitting_dates import fitDates
from sysquant.estimators.correlations import Correlation

class exponentialCorrelation(object):
    def __init__(self, data_for_correlation,
                 ew_lookback:int =250,
                 min_periods:int=20,
                 cleaning:bool = True,
                 floor_at_zero:bool = True,
                 length_adjustment: int = 1,
                 **_ignored_kwargs):


        cleaning = str2Bool(cleaning)
        floor_at_zero = str2Bool(floor_at_zero)

        self._cleaning = cleaning
        self._floor_at_zero = floor_at_zero

        correlation_calculations = exponentialCorrelationResults(data_for_correlation,
                                                                 ew_lookback=ew_lookback,
                                                                 min_periods=min_periods,
                                                                 length_adjustment=length_adjustment)

        self._correlation_calculations  = correlation_calculations
        self._data_for_correlation = data_for_correlation

    @property
    def cleaning(self) -> bool:
        return self._cleaning

    @property
    def floor_at_zero(self) -> bool:
        return self._floor_at_zero

    @property
    def correlation_calculations(self):
        return self._correlation_calculations

    @property
    def data_for_correlation(self):
        return self._data_for_correlation

    def get_corr_mat_for_fitperiod(self, fit_period: fitDates):
        if fit_period.no_data:
            return missing_data

        raw_corr_matrix = self._get_raw_corr_for_datetime(fit_period)

        cleaning = self.cleaning
        if cleaning:
            data_for_correlation = self.data_for_correlation
            cleaned_corr_matrix = raw_corr_matrix.clean_corr_matrix_given_data(
                                                               fit_period,
                                                               data_for_correlation)
        else:
            cleaned_corr_matrix = raw_corr_matrix

        floor_at_zero = self.floor_at_zero
        if floor_at_zero:
            corr_matrix = cleaned_corr_matrix.floor_correlation_matrix(floor = 0.0)
        else:
            corr_matrix = cleaned_corr_matrix

        return corr_matrix

    def _get_raw_corr_for_datetime(self, fit_period: fitDates) -> Correlation:
        correlation_calculations = self.correlation_calculations
        last_date_in_fit_period = fit_period.fit_end
        ## some kind of access
        raw_corr_matrix = correlation_calculations.\
            last_valid_cor_matrix_for_date(last_date_in_fit_period)

        return raw_corr_matrix



class exponentialCorrelationResults(object):
    def __init__(self, data_for_correlation,
                 ew_lookback:int =250,
                 min_periods:int=20,
                 length_adjustment: int = 1,
                 **_ignored_kwargs):

        columns = data_for_correlation.columns
        self._columns = columns

        adjusted_lookback = ew_lookback * length_adjustment
        adjusted_min_periods = min_periods * length_adjustment

        raw_correlations = data_for_correlation.ewm(
            span=adjusted_lookback,
            min_periods=adjusted_min_periods).corr(
            pairwise=True)

        self._raw_correlations = raw_correlations

    @property
    def raw_correlations(self):
        return self._raw_correlations

    def last_valid_cor_matrix_for_date(self, date_point: datetime.datetime) -> Correlation:
        first_index, last_index = self._range_of_indices_for_date(date_point)
        raw_correlations = self.raw_correlations

        # slicing is weird
        corr_matrix_values = raw_correlations[(first_index+1):(last_index+1)].values
        columns = self.columns

        return Correlation(values=corr_matrix_values, columns=columns)

    def _range_of_indices_for_date(self, date_point: datetime.datetime) -> (int, int):
        last_index = self._index_of_datetime_in_data(date_point)
        size_of_matrix = self.size_of_matrix
        first_index = last_index - size_of_matrix

        return first_index, last_index

    @property
    def size_of_matrix(self) -> int:
        return len(self.columns)

    @property
    def columns(self)-> list:
        return self._columns

    def _index_of_datetime_in_data(self, date_point: datetime.datetime) -> int:
        ts_index = self.index
        xpoint = [index_idx for index_idx, index_date in
                  enumerate(ts_index) if index_date<date_point]
        if len(xpoint)==0:
            return 0

        last_index = xpoint[-1]

        return last_index

    @property
    def index(self) -> list:
        # don't recalculate as slow
        ts_index = getattr(self, "_ts_index", None)
        if ts_index is None:
            ts_index = self._ts_index = \
                self._calculate_index_of_timestampes_in_raw_correlations()

        return ts_index

    def _calculate_index_of_timestampes_in_raw_correlations(self) -> list:
        raw_correlations = self.raw_correlations
        ts_index = [x[0] for x in raw_correlations.index]

        return ts_index

## ADD METHOD TO RETRIEVE SPECIFIC DATE