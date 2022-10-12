import numpy as np

import pandas as pd

from sysquant.estimators.correlations import CorrelationList, correlationEstimate
from sysquant.optimisation.weights import portfolioWeights


def diversification_multiplier_from_list(
    correlation_list: CorrelationList,
    weight_df: pd.DataFrame,
    ewma_span: int = 125,
    **kwargs
) -> pd.Series:
    # FIXME THE FREQUENCY OF WEIGHT_DF MAY NOT MATCH EMWA_SPAN WHICH IS UNITLES IN ANY CASE...
    """
    Given a CorrelationList object, and a dataframe of weights, work out the div multiplier

    :param correlation_list_object: CorrelationList to use for calculation
    :type correlation_list_object: CorrelationList

    :param weight_df_raw: Weights of assets
    :type weight_df_raw: TxN pd.DataFrame

    :param ewma_span: Smoothing parameter to use on output (1= no smoothing)
    :type ewma_span: int

    :param max: Maximum allowable value
    :type max: float

    :param **kwargs: Used for single period calculation

    :returns: Tx1 pd.Series

    """
    # align weights to corr list columns
    weight_df_aligned = weight_df[correlation_list.column_names]

    ref_periods = [fit_period.period_start for fit_period in correlation_list.fit_dates]

    # here's where we stack up the answers
    div_mult_vector = []

    for (corrmatrix, start_of_period) in zip(correlation_list.corr_list, ref_periods):

        weight_slice = weight_df_aligned[:start_of_period]
        if weight_slice.shape[0] == 0:
            # empty space
            div_mult_vector.append(1.0)
            continue

        # take the current weights and work out the DM
        weights_dict = weight_slice.iloc[-1].to_dict()
        weights = portfolioWeights(weights_dict)
        div_multiplier = diversification_mult_single_period(
            corrmatrix, weights, **kwargs
        )

        div_mult_vector.append(div_multiplier)

    # In same space as correlations probably annually
    div_mult_df = pd.Series(div_mult_vector, index=ref_periods)

    # Change to business days, so moving average will make sense, aligned to original weights
    div_mult_df_daily = div_mult_df.reindex(weight_df_aligned.index, method="ffill")

    ## Leading Nans, just use 1.0
    div_mult_df_daily[div_mult_df_daily.isna()] = 1.0

    # take a moving average to smooth the jumps
    div_mult_df_smoothed = div_mult_df_daily.ewm(span=ewma_span).mean()

    return div_mult_df_smoothed


def diversification_mult_single_period(
    corrmatrix: correlationEstimate, weights: portfolioWeights, dm_max: float = 2.5
) -> float:
    """
    Given N assets with a correlation matrix of H and  weights W summing to 1,
    the diversification multiplier will be 1 / [ ( W x H x WT ) 1/2 ]

    """
    try:
        risk = weights.portfolio_stdev(corrmatrix)
    except:
        risk = np.nan

    if np.isnan(risk):
        return 1.0

    if risk < 0.0000001:
        return 1.0

    dm = np.min([1.0 / risk, dm_max])

    return dm
