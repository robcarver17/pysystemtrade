import pandas as pd
from syscore.genutils import progressBar

from sysquant.fitting_dates import fitDates, generate_fitting_dates
from sysquant.estimators.correlations import CorrelationList, Correlation, create_boring_corr_matrix
from sysquant.estimators.exponential_correlation import exponentialCorrelation

def correlation_over_time_for_returns(returns_for_correlation: pd.DataFrame,
                                      frequency="W",
                                      forward_fill_price_index=True,
                                      **kwargs
                                      ) -> CorrelationList:

    index_prices_for_correlation = returns_for_correlation.cumsum()
    if forward_fill_price_index:
        index_prices_for_correlation = index_prices_for_correlation.ffill()

    index_prices_for_correlation = index_prices_for_correlation.resample(frequency).last()
    returns_for_correlation = index_prices_for_correlation.diff()

    correlation_list = correlation_over_time(returns_for_correlation,
                                             **kwargs)

    return correlation_list

def correlation_over_time(data_for_correlation: pd.DataFrame,
                          date_method="expanding",
                          rollyears=20,
                          **kwargs
                          ) -> CorrelationList:

    column_names = list(data_for_correlation.columns)

    # Generate time periods
    fit_dates = generate_fitting_dates(
        data_for_correlation, date_method=date_method, rollyears=rollyears
    )

    progress = progressBar(len(fit_dates), "Estimating correlations")

    correlation_estimator_for_one_period = correlationSinglePeriod(
        data_for_correlation, **kwargs
    )

    corr_list = []
    # Now for each time period, estimate correlation
    for fit_period in fit_dates:
        progress.iterate()
        corrmat = correlation_estimator_for_one_period.calculate_correlation_for_period(
            fit_period)
        corr_list.append(corrmat)

    correlation_list = CorrelationList(corr_list = corr_list, column_names = column_names,
                    fit_dates=fit_dates)

    return correlation_list




class correlationSinglePeriod(object):
    def __init__(
        self,
        data_for_correlation: pd.DataFrame,
        using_exponent: bool = True,
        **kwargs
    ):
        self._data_for_correlation = data_for_correlation
        self._using_exponent = using_exponent
        self._kwargs = kwargs

    @property
    def using_exponent(self) -> bool:
        return self._using_exponent

    @property
    def data_for_correlation(self):
        return self._data_for_correlation

    @property
    def kwargs_for_estimator(self) -> dict:
        return self._kwargs

    def calculate_correlation_for_period(self, fit_period: fitDates) -> Correlation:
        if fit_period.no_data:
            return self.corr_matrix_if_no_data()

        if self.using_exponent:
            corr_matrix = self.calculate_correlation_using_exponential_data_for_period(fit_period)
        else:
            corr_matrix = self.calculate_correlation_normally(fit_period)

        return corr_matrix

    def calculate_correlation_normally(self, fit_period: fitDates) -> Correlation:
        data_for_correlation = self.data_for_correlation
        kwargs_for_estimator = self.kwargs_for_estimator
        corr_matrix = correlation_estimator_for_subperiod(data_for_correlation=data_for_correlation,
                                                          fit_period=fit_period,
                                                          **kwargs_for_estimator)

        return corr_matrix

    def calculate_correlation_using_exponential_data_for_period(self, fit_period: fitDates) -> Correlation:
        exponential_correlation = self.get_exponential_correlation_for_entire_dataset()

        corr_matrix = exponential_correlation.get_corr_mat_for_fitperiod(fit_period)

        return corr_matrix

    def get_exponential_correlation_for_entire_dataset(self) -> exponentialCorrelation:
        exponential_correlation = getattr(self, "_stored_exponential_correlation", None)
        if exponential_correlation is None:
            exponential_correlation = self.calculate_exponential_correlation_for_entire_dataset()
            self._stored_exponential_correlation = exponential_correlation

        return exponential_correlation

    def calculate_exponential_correlation_for_entire_dataset(self) -> exponentialCorrelation:
        kwargs_for_estimator = self.kwargs_for_estimator
        exponential_correlation = \
            exponentialCorrelation(self.data_for_correlation, **kwargs_for_estimator)

        return exponential_correlation

    def corr_matrix_if_no_data(self) -> Correlation:
        columns = self.data_for_correlation.columns
        size = len(columns)

        return create_boring_corr_matrix(size)

def correlation_estimator_for_subperiod(data_for_correlation,
                                                     fit_period: fitDates,
                          cleaning: bool = True,
                          floor_at_zero: bool = True,
                          **_ignored_kwargs):

    subperiod_data = data_for_correlation[fit_period.fit_start: fit_period.fit_end]

    corr_matrix_values = subperiod_data.corr()
    corr_matrix = Correlation(corr_matrix_values, data_for_correlation.columns)
    if cleaning:
        corr_matrix = corr_matrix.clean_corr_matrix_given_data(data_for_correlation=data_for_correlation,
                                                               fit_period=fit_period)

    if floor_at_zero:
        corr_matrix = corr_matrix.floor_correlation_matrix(floor = 0.0)

    return corr_matrix

