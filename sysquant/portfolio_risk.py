import datetime
import pandas as pd
from syscore.interactive.progress_bar import progressBar

from sysquant.estimators.stdev_estimator import seriesOfStdevEstimates, stdevEstimates
from sysquant.estimators.correlations import (
    correlationEstimate,
    create_boring_corr_matrix,
    CorrelationList,
)
from sysquant.estimators.covariance import (
    covarianceEstimate,
    covariance_from_stdev_and_correlation,
)
from sysquant.optimisation.weights import seriesOfPortfolioWeights


def calc_sum_annualised_risk_given_portfolio_weights(
    portfolio_weights: seriesOfPortfolioWeights, pd_of_stdev: seriesOfStdevEstimates
) -> pd.Series:

    instrument_list = list(portfolio_weights.columns)
    aligned_stdev = pd_of_stdev[instrument_list].reindex(portfolio_weights.index)

    risk_df = aligned_stdev * portfolio_weights.abs()
    risk_series = risk_df.sum(axis=1)

    return risk_series


def calc_portfolio_risk_series(
    portfolio_weights: seriesOfPortfolioWeights,
    list_of_correlations: CorrelationList,
    pd_of_stdev: seriesOfStdevEstimates,
) -> pd.Series:

    risk_series = []
    common_index = list(portfolio_weights.index)
    progress = progressBar(
        len(common_index),
        suffix="Calculating portfolio risk",
        show_each_time=False,
        show_timings=True,
    )

    for relevant_date in common_index:
        progress.iterate()
        weights_on_date = portfolio_weights.get_weights_on_date(relevant_date)

        covariance = get_covariance_matrix(
            list_of_correlations=list_of_correlations,
            pd_of_stdev=pd_of_stdev,
            relevant_date=relevant_date,
        )
        risk_on_date = weights_on_date.portfolio_stdev(covariance)
        risk_series.append(risk_on_date)

    progress.close()
    risk_series = pd.Series(risk_series, common_index)

    return risk_series


def get_covariance_matrix(
    list_of_correlations: CorrelationList,
    pd_of_stdev: seriesOfStdevEstimates,
    relevant_date: datetime.datetime,
) -> covarianceEstimate:

    instrument_list = list(pd_of_stdev.columns)
    correlation_estimate = get_correlation_matrix(
        relevant_date=relevant_date,
        list_of_correlations=list_of_correlations,
        instrument_list=instrument_list,
    )

    stdev_estimate = get_stdev_estimate(
        relevant_date=relevant_date, pd_of_stdev=pd_of_stdev
    )

    covariance = covariance_from_stdev_and_correlation(
        correlation_estimate, stdev_estimate
    )

    return covariance


def get_correlation_matrix(
    relevant_date: datetime.datetime,
    list_of_correlations: CorrelationList,
    instrument_list: list,
) -> correlationEstimate:
    try:
        correlation_matrix = list_of_correlations.most_recent_correlation_before_date(
            relevant_date
        )
    except:
        correlation_matrix = create_boring_corr_matrix(
            len(instrument_list), columns=instrument_list, offdiag=0.0
        )

    return correlation_matrix


def get_stdev_estimate(
    pd_of_stdev: seriesOfStdevEstimates, relevant_date: datetime.datetime
) -> stdevEstimates:
    stdev_estimate = pd_of_stdev.get_stdev_on_date(relevant_date)

    return stdev_estimate
